"""Small deterministic corridor replay; all passenger outputs are synthetic."""

from dataclasses import dataclass
from functools import lru_cache
from math import ceil, floor

from paddydash.services.mobility_config import default_mobility_config
from paddydash.services.mobility_contract import (
    EdgeState, MobilityConfig, NodeState, PhaseId, ScenarioId, SimulationSnapshot,
)


@dataclass(frozen=True)
class MobilityRun:
    snapshots: tuple[SimulationSnapshot, ...]
    peak_queue: int
    delay_person_minutes: int
    overloaded_steps: int
    clearance_minutes: int | None
    peak_utilization: float
    completed: bool


def run_simulation(config: MobilityConfig, scenario_id: ScenarioId | str,
                   max_post_match_minutes: int = 720) -> MobilityRun:
    """Replay one cohort through arrival, holding and departure on a linear corridor.

    Each timestamp records arrivals, release and service at that boundary.
    Transit arrivals are processed before new admissions; every edge takes at
    least one step. Terminal service has no additional capacity constraint.
    """
    scenario_id = ScenarioId(scenario_id)
    scenario = next((s for s in config.scenarios if s.scenario_id == scenario_id), None)
    if scenario is None:
        raise ValueError('Scenario is not configured')
    if max_post_match_minutes <= 0:
        raise ValueError('Simulation horizon must be positive')
    dt = config.time_step_minutes
    demand = config.demand
    nodes = config.nodes
    if (demand.arrival_node, demand.venue_node, demand.exit_node) != (
        nodes[0].node_id, nodes[-1].node_id, nodes[0].node_id
    ):
        raise ValueError('The replay requires an end-to-end corridor and return trip')
    pairs = {(edge.from_node, edge.to_node): edge for edge in config.edges}
    required = {(a.node_id, b.node_id) for a, b in zip(nodes, nodes[1:])}
    required |= {(b, a) for a, b in required}
    if len(pairs) != len(config.edges) or set(pairs) != required:
        raise ValueError('The replay requires exactly two directed edges per adjacent leg')
    times = {phase.phase_id: phase.start_minute for phase in config.phases}
    whistle = times[PhaseId.FINAL_WHISTLE]
    gates = times.get(PhaseId.GATES_OPEN, config.phases[0].start_minute)
    arrival_steps = (demand.arrival_end_minute - demand.arrival_start_minute) // dt
    release_steps = ceil(demand.departure_duration_minutes * scenario.departure_duration_multiplier / dt)
    capacities = {}
    travel = {}
    for edge in config.edges:
        affected = edge.mode in scenario.affected_modes
        capacities[edge.edge_id] = floor(edge.base_capacity_per_step * (
            scenario.capacity_multiplier if affected else 1
        ))
        travel[edge.edge_id] = max(1, ceil(edge.travel_time_minutes * (
            scenario.travel_time_multiplier if affected else 1
        ) / dt)) * dt
    queues = {(node.node_id, direction): 0 for node in nodes for direction in (1, -1)}
    # Batches retain direction, destination, edge and completion time.
    transit: list[tuple[int, str, int, str, int]] = []
    holding = entered = released = exited = 0
    snapshots = []
    delay = overloaded = peak_queue = 0
    peak_utilization = 0.0
    clearance = None
    for minute in range(config.phases[0].start_minute, whistle + max_post_match_minutes + 1, dt):
        incoming = {n.node_id: 0 for n in nodes}
        served = dict(incoming)
        departing = dict(incoming)
        remaining = []
        for arrival, destination, direction, edge_id, count in transit:
            if arrival <= minute:
                queues[destination, direction] += count
                incoming[destination] += count
            else:
                remaining.append((arrival, destination, direction, edge_id, count))
        transit = remaining
        if demand.arrival_start_minute <= minute < demand.arrival_end_minute:
            step = (minute - demand.arrival_start_minute) // dt
            count = demand.cohort_size * (step + 1) // arrival_steps - demand.cohort_size * step // arrival_steps
            queues[demand.arrival_node, 1] += count
            incoming[demand.arrival_node] += count
            entered += count
        terminal_service = set()
        if minute >= gates:
            count = queues[demand.venue_node, 1]
            holding += count
            queues[demand.venue_node, 1] = 0
            served[demand.venue_node] += count
            if count:
                terminal_service.add(demand.venue_node)
        count = queues[demand.exit_node, -1]
        exited += count
        served[demand.exit_node] += count
        departing[demand.exit_node] += count
        queues[demand.exit_node, -1] = 0
        if count:
            terminal_service.add(demand.exit_node)
        if minute >= whistle:
            target = demand.cohort_size * min(release_steps, (minute - whistle) // dt + 1) // release_steps
            count = min(holding, max(0, target - released))
            holding -= count
            released += count
            queues[demand.venue_node, -1] += count
        edge_flows = {}
        node_capacities = {n.node_id: 0 for n in nodes}
        waits = {n.node_id: [] for n in nodes}
        if queues[demand.venue_node, 1]:
            waits[demand.venue_node].append(float(max(0, gates - minute)))
        for index, node in enumerate(nodes):
            for direction in (1, -1):
                target_index = index + direction
                if not 0 <= target_index < len(nodes):
                    continue
                edge = pairs[node.node_id, nodes[target_index].node_id]
                requested = queues[node.node_id, direction]
                capacity = capacities[edge.edge_id]
                count = min(requested, capacity)
                queues[node.node_id, direction] -= count
                served[node.node_id] += count
                departing[node.node_id] += count
                if requested:
                    node_capacities[node.node_id] += capacity
                if count:
                    transit.append((minute + travel[edge.edge_id], edge.to_node, direction, edge.edge_id, count))
                backlog = queues[node.node_id, direction]
                if backlog:
                    waits[node.node_id].append(ceil(backlog / capacity) * dt if capacity else None)
                edge_flows[edge.edge_id] = (requested, capacity, count)
        edge_states = tuple(
            EdgeState(edge_id=edge.edge_id, demand=edge_flows[edge.edge_id][0],
                      capacity=edge_flows[edge.edge_id][1], throughput=edge_flows[edge.edge_id][2],
                      utilization=edge_flows[edge.edge_id][2] / capacities[edge.edge_id] if capacities[edge.edge_id] else 0,
                      in_transit_passengers=sum(batch[4] for batch in transit if batch[3] == edge.edge_id))
            for edge in config.edges
        )
        node_states = tuple(
            NodeState(node_id=node.node_id, incoming_passengers=incoming[node.node_id],
                      queue=sum(queues[node.node_id, d] for d in (1, -1)),
                      served_passengers=served[node.node_id], departing_passengers=departing[node.node_id],
                      holding_passengers=holding if node.node_id == demand.venue_node else 0,
                      utilization=None if node.node_id in terminal_service else (
                          served[node.node_id] / node_capacities[node.node_id] if node_capacities[node.node_id] else 0
                      ),
                      estimated_wait_minutes=None if None in waits[node.node_id] else max(waits[node.node_id], default=0))
            for node in nodes
        )
        phase = max((p for p in config.phases if p.kind == 'interval' and p.start_minute <= minute),
                    key=lambda p: p.start_minute)
        snapshot = SimulationSnapshot(
            config_id=config.config_id, scenario_id=scenario_id, phase_id=phase.phase_id,
            time_minutes=minute, node_states=node_states, edge_states=edge_states,
            total_entered=entered, total_people_in_system=entered - exited, total_served=exited,
            assumptions=config.assumptions + scenario.assumptions,
        )
        snapshot.validate_against(config)
        snapshots.append(snapshot)
        queue = sum(n.queue for n in node_states)
        peak_queue = max(peak_queue, queue)
        delay += queue * dt
        overloaded += int(any(e.demand > e.capacity for e in edge_states))
        peak_utilization = max(peak_utilization, *(e.utilization for e in edge_states))
        if minute >= whistle and exited == demand.cohort_size:
            clearance = minute - whistle
            break
    return MobilityRun(tuple(snapshots), peak_queue, delay, overloaded, clearance,
                       peak_utilization, clearance is not None)


@lru_cache(maxsize=5)
def default_run(scenario_id: str) -> MobilityRun:
    """Cache immutable default runs; no data or model provider is contacted."""
    return run_simulation(default_mobility_config(), scenario_id)
