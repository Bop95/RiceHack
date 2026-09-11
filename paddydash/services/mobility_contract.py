"""Validated, UI-independent contracts for a future discrete-step corridor model."""

from enum import Enum
from typing import Annotated, Literal, Self

from pydantic import BaseModel, ConfigDict, Field, model_validator


Count = Annotated[int, Field(strict=True, ge=0)]
PositiveCount = Annotated[int, Field(strict=True, gt=0)]
Minutes = Annotated[int, Field(strict=True)]
Nonnegative = Annotated[float, Field(ge=0)]
Ratio = Annotated[float, Field(ge=0, le=1)]
Identifier = Annotated[str, Field(pattern=r'^[a-z][a-z0-9_]*$')]
Text = Annotated[str, Field(min_length=1, pattern=r'\S')]


class ScenarioId(str, Enum):
    BASELINE = 'baseline'
    RAIL_DISRUPTION = 'rail_disruption'
    RAIL_CAPACITY_BOOST = 'rail_capacity_boost'
    RAIN = 'rain'
    STAGGERED_DEPARTURE = 'staggered_departure'


class PhaseId(str, Enum):
    PRE_MATCH = 'pre_match'
    GATES_OPEN = 'gates_open'
    CEREMONY = 'ceremony'
    KICKOFF = 'kickoff'
    FIRST_HALF = 'first_half'
    FIRST_HALF_END = 'first_half_end'
    HALFTIME = 'halftime'
    SECOND_HALF = 'second_half'
    REGULATION_END = 'regulation_end'
    EXTRA_TIME = 'extra_time'
    EXTRA_TIME_END = 'extra_time_end'
    FINAL_WHISTLE = 'final_whistle'
    POST_MATCH = 'post_match'


Mode = Literal['walk', 'rail', 'road', 'shuttle']


class ContractModel(BaseModel):
    model_config = ConfigDict(extra='forbid', frozen=True, allow_inf_nan=False)


class CorridorNode(ContractModel):
    node_id: Identifier
    name: Text
    node_type: Literal['origin', 'station', 'venue']
    order: Count


class CorridorEdge(ContractModel):
    edge_id: Identifier
    from_node: Identifier
    to_node: Identifier
    mode: Mode
    base_capacity_per_step: PositiveCount
    travel_time_minutes: Nonnegative
    data_type: Literal['synthetic', 'derived'] = 'synthetic'
    source_reference: Text | None = None

    @model_validator(mode='after')
    def validate_edge(self) -> Self:
        if self.from_node == self.to_node:
            raise ValueError('An edge must connect distinct nodes')
        if self.data_type == 'derived' and self.source_reference is None:
            raise ValueError('Derived capacity/travel inputs require a source reference')
        return self


class MatchPhase(ContractModel):
    phase_id: PhaseId
    display_label: Text
    order: Count
    start_minute: Minutes
    clock_reference: Text
    kind: Literal['event', 'interval']
    simulation_meaning: Text


class Scenario(ContractModel):
    scenario_id: ScenarioId
    display_label: Text
    affected_modes: tuple[Mode, ...] = ()
    capacity_multiplier: Annotated[float, Field(ge=0)] = 1.0
    travel_time_multiplier: Annotated[float, Field(gt=0)] = 1.0
    departure_duration_multiplier: Annotated[float, Field(ge=1)] = 1.0
    assumptions: tuple[Text, ...] = Field(min_length=1)

    @model_validator(mode='after')
    def validate_modifiers(self) -> Self:
        if self.scenario_id == ScenarioId.BASELINE and (
            self.capacity_multiplier != 1 or self.travel_time_multiplier != 1
            or self.departure_duration_multiplier != 1
        ):
            raise ValueError('Baseline modifiers must equal one')
        if not self.affected_modes and (
            self.capacity_multiplier != 1 or self.travel_time_multiplier != 1
        ):
            raise ValueError('Edge modifiers require explicit affected modes')
        return self


class DemandAssumptions(ContractModel):
    cohort_size: PositiveCount
    arrival_node: Identifier
    venue_node: Identifier
    exit_node: Identifier
    arrival_start_minute: Minutes
    arrival_end_minute: Minutes
    departure_duration_minutes: PositiveCount
    distribution: Literal['uniform'] = 'uniform'
    data_type: Literal['synthetic', 'derived'] = 'synthetic'
    source_reference: Text | None = None

    @model_validator(mode='after')
    def validate_demand(self) -> Self:
        if self.arrival_end_minute <= self.arrival_start_minute:
            raise ValueError('Arrival window must have positive duration')
        if self.data_type == 'derived' and self.source_reference is None:
            raise ValueError('Derived demand inputs require a source reference')
        return self


def require_unique(values: list[object], description: str) -> None:
    if len(values) != len(set(values)):
        raise ValueError(f'{description} must be unique')


class MobilityConfig(ContractModel):
    config_id: Identifier
    time_step_minutes: PositiveCount
    nodes: tuple[CorridorNode, ...] = Field(min_length=2)
    edges: tuple[CorridorEdge, ...] = Field(min_length=1)
    phases: tuple[MatchPhase, ...] = Field(min_length=1)
    scenarios: tuple[Scenario, ...] = Field(min_length=1)
    demand: DemandAssumptions
    assumptions: tuple[Text, ...] = Field(min_length=1)

    @model_validator(mode='after')
    def validate_configuration(self) -> Self:
        require_unique([n.node_id for n in self.nodes], 'Node IDs')
        require_unique([e.edge_id for e in self.edges], 'Edge IDs')
        require_unique([p.phase_id for p in self.phases], 'Phase IDs')
        require_unique([s.scenario_id for s in self.scenarios], 'Scenario IDs')
        if [n.order for n in self.nodes] != list(range(len(self.nodes))):
            raise ValueError('Nodes must be in contiguous corridor order starting at zero')
        if [p.order for p in self.phases] != list(range(len(self.phases))):
            raise ValueError('Phases must be in contiguous display order starting at zero')
        phase_ranks = [list(PhaseId).index(p.phase_id) for p in self.phases]
        if phase_ranks != sorted(phase_ranks):
            raise ValueError('Phases must follow canonical match order')
        starts = [p.start_minute for p in self.phases]
        if starts != sorted(starts):
            raise ValueError('Phases must be ordered by elapsed start minute')
        interval_starts = [p.start_minute for p in self.phases if p.kind == 'interval']
        require_unique(interval_starts, 'Interval start minutes')
        node_ids = {n.node_id for n in self.nodes}
        if any(e.from_node not in node_ids or e.to_node not in node_ids for e in self.edges):
            raise ValueError('Every edge endpoint must reference a configured node')
        if not {self.demand.arrival_node, self.demand.venue_node, self.demand.exit_node} <= node_ids:
            raise ValueError('Demand endpoints must reference configured nodes')
        if ScenarioId.BASELINE not in {s.scenario_id for s in self.scenarios}:
            raise ValueError('A baseline scenario is required')
        phase_times = {p.phase_id: p.start_minute for p in self.phases}
        if phase_times.get(PhaseId.KICKOFF) != 0:
            raise ValueError('Kickoff must be the zero-minute clock reference')
        if PhaseId.FINAL_WHISTLE not in phase_times:
            raise ValueError('A final whistle is required to release the held cohort')
        if self.demand.arrival_start_minute < starts[0]:
            raise ValueError('Arrival demand cannot precede the configured timeline')
        if self.demand.arrival_end_minute > phase_times[PhaseId.FINAL_WHISTLE]:
            raise ValueError('Arrival demand must end by final whistle')
        aligned_times = [*starts, self.demand.arrival_start_minute,
                         self.demand.arrival_end_minute, self.demand.departure_duration_minutes]
        if any(t % self.time_step_minutes for t in aligned_times):
            raise ValueError('Phase and demand boundaries must align with the time step')
        return self


class NodeState(ContractModel):
    node_id: Identifier
    incoming_passengers: Count
    queue: Count
    served_passengers: Count
    departing_passengers: Count
    holding_passengers: Count = 0
    utilization: Ratio | None
    estimated_wait_minutes: Nonnegative | None

    @model_validator(mode='after')
    def validate_departures(self) -> Self:
        if self.departing_passengers > self.served_passengers:
            raise ValueError('Node departures cannot exceed passengers served in the step')
        return self


class EdgeState(ContractModel):
    edge_id: Identifier
    demand: Count
    capacity: Count
    throughput: Count
    utilization: Ratio
    in_transit_passengers: Count = 0

    @model_validator(mode='after')
    def validate_flow(self) -> Self:
        if self.throughput > min(self.demand, self.capacity):
            raise ValueError('Throughput cannot exceed demand or capacity')
        expected = self.throughput / self.capacity if self.capacity else 0.0
        if abs(self.utilization - expected) > 1e-9:
            raise ValueError('Edge utilization must equal throughput / capacity (zero if closed)')
        return self


class SimulationSnapshot(ContractModel):
    config_id: Identifier
    scenario_id: ScenarioId
    phase_id: PhaseId
    time_minutes: Minutes
    node_states: tuple[NodeState, ...]
    edge_states: tuple[EdgeState, ...]
    total_entered: Count
    total_people_in_system: Count
    total_served: Count
    data_type: Literal['synthetic'] = 'synthetic'
    assumptions: tuple[Text, ...] = Field(min_length=1)

    @model_validator(mode='after')
    def validate_totals(self) -> Self:
        require_unique([n.node_id for n in self.node_states], 'Snapshot node IDs')
        require_unique([e.edge_id for e in self.edge_states], 'Snapshot edge IDs')
        inventory = sum(n.queue + n.holding_passengers for n in self.node_states)
        inventory += sum(e.in_transit_passengers for e in self.edge_states)
        if self.total_people_in_system != inventory:
            raise ValueError('System inventory must include queues, holding, and in-transit people')
        if self.total_entered != self.total_people_in_system + self.total_served:
            raise ValueError('Entered cohort must equal current inventory plus completed exits')
        return self

    def validate_against(self, config: MobilityConfig) -> None:
        """Check references against the configuration used to produce this snapshot."""
        if self.config_id != config.config_id:
            raise ValueError('Snapshot config_id does not match')
        if {n.node_id for n in self.node_states} != {n.node_id for n in config.nodes}:
            raise ValueError('Snapshot must contain every configured node exactly once')
        if {e.edge_id for e in self.edge_states} != {e.edge_id for e in config.edges}:
            raise ValueError('Snapshot must contain every configured edge exactly once')
        if self.scenario_id not in {s.scenario_id for s in config.scenarios}:
            raise ValueError('Snapshot scenario is not configured')
        phase = next((p for p in config.phases if p.phase_id == self.phase_id), None)
        if phase is None or self.time_minutes < phase.start_minute:
            raise ValueError('Snapshot phase is absent or has not started')
        if phase.kind == 'event' and self.time_minutes != phase.start_minute:
            raise ValueError('Event snapshots must occur at their marker time')
        later_intervals = [p.start_minute for p in config.phases
                           if p.kind == 'interval' and p.start_minute > phase.start_minute]
        if phase.kind == 'interval' and later_intervals and self.time_minutes >= min(later_intervals):
            raise ValueError('Snapshot interval has already ended')
        if self.time_minutes % config.time_step_minutes:
            raise ValueError('Snapshot time must align with the configured step')
        if self.total_entered > config.demand.cohort_size:
            raise ValueError('Entered people cannot exceed the configured cohort')
