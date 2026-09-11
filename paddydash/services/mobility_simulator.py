"""Deterministic corridor replays for default and time-varying synthetic inputs."""

from collections import defaultdict
from dataclasses import dataclass
from functools import lru_cache
from math import ceil, floor
from typing import Any, Iterable

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


@dataclass(frozen=True)
class ProfileNodeState:
    """Derived node state from the generated demand/capacity input profiles."""

    node_id: str
    incoming_passengers: int
    queue_passengers: int
    served_passengers: int
    departing_passengers: int
    utilization: float | None
    estimated_wait_minutes: float | None
    holding_passengers: int


@dataclass(frozen=True)
class ProfileEdgeState:
    """Derived edge state at one replay boundary."""

    edge_id: str
    demand: int
    capacity: int
    throughput: int
    utilization: float
    in_transit_passengers: int


@dataclass(frozen=True)
class ProfileSnapshot:
    """One derived profile replay boundary; all values trace to synthetic inputs."""

    scenario_id: str
    timestamp: str
    time_minutes: int
    phase_id: str
    node_states: tuple[ProfileNodeState, ...]
    edge_states: tuple[ProfileEdgeState, ...]
    total_entered: int
    total_people_in_system: int
    total_exited: int


@dataclass(frozen=True)
class ProfileMobilityRun:
    """Derived output for one scenario using generated time-varying profiles."""

    snapshots: tuple[ProfileSnapshot, ...]
    peak_queue: int
    bottleneck_node: str | None
    delay_person_minutes: int
    overloaded_intervals: int
    clearance_minutes: int | None
    peak_utilization: float
    total_arrivals: int
    total_departures: int
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


def run_profile_simulation(
    config: MobilityConfig,
    scenario_id: ScenarioId | str,
    demand_rows: Iterable[dict[str, Any]],
    capacity_rows: Iterable[dict[str, Any]],
) -> ProfileMobilityRun:
    """Replay one input-profile scenario on the existing linear corridor.

    Rail and walk rows use configured physical edges. Road and shuttle rows are
    direct-access inputs because the shared corridor has no road/shuttle edges;
    they enter stadium holding or exit at the stadium boundary. This keeps their
    accounting explicit without inventing a second transport graph.
    """
    selected = ScenarioId(scenario_id).value
    dt = config.time_step_minutes
    nodes = config.nodes
    node_ids = [node.node_id for node in nodes]
    node_index = {node.node_id: index for index, node in enumerate(nodes)}
    edge_by_pair = {(edge.from_node, edge.to_node): edge for edge in config.edges}
    profile_demand = [row for row in demand_rows if row["scenario_id"] == selected]
    profile_capacity = [row for row in capacity_rows if row["scenario_id"] == selected]
    if not profile_demand or not profile_capacity:
        raise ValueError("Selected scenario has no demand or capacity profile rows")
    times = sorted({int(row["time_minutes"]) for row in profile_demand})
    if times != list(range(times[0], times[-1] + dt, dt)):
        raise ValueError("Demand profile time range must be contiguous and aligned")
    demand_at: dict[tuple[int, str], list[dict[str, Any]]] = defaultdict(list)
    phase_at: dict[int, str] = {}
    timestamp_at: dict[int, str] = {}
    for row in profile_demand:
        minute = int(row["time_minutes"])
        if minute % dt or row["phase_id"] not in {phase.phase_id.value for phase in config.phases}:
            raise ValueError("Demand profile contains an invalid time or phase")
        demand_at[minute, row["direction"]].append(row)
        phase_at.setdefault(minute, row["phase_id"])
        timestamp_at.setdefault(minute, row["timestamp"])
        if phase_at[minute] != row["phase_id"] or timestamp_at[minute] != row["timestamp"]:
            raise ValueError("Demand profile has inconsistent phase or timestamp values")
    capacity_at: dict[tuple[int, str], int] = {}
    for row in profile_capacity:
        minute, edge_id = int(row["time_minutes"]), row["edge_id"]
        if edge_id not in {edge.edge_id for edge in config.edges}:
            raise ValueError("Capacity profile references an unknown edge")
        if (minute, edge_id) in capacity_at:
            raise ValueError("Capacity profile has duplicate scenario/time/edge rows")
        capacity_at[minute, edge_id] = int(row["effective_capacity"])
    for minute in times:
        if {edge.edge_id for edge in config.edges} != {edge_id for current, edge_id in capacity_at if current == minute}:
            raise ValueError("Capacity profile must contain every edge at every replay boundary")

    scenario = next(item for item in config.scenarios if item.scenario_id.value == selected)
    travel_minutes = {
        edge.edge_id: max(1, ceil(edge.travel_time_minutes * (
            scenario.travel_time_multiplier if edge.mode in scenario.affected_modes else 1
        ) / dt)) * dt
        for edge in config.edges
    }
    gates = next(phase.start_minute for phase in config.phases if phase.phase_id == PhaseId.GATES_OPEN)
    whistle = next(phase.start_minute for phase in config.phases if phase.phase_id == PhaseId.FINAL_WHISTLE)
    queues: dict[tuple[str, int, str], int] = defaultdict(int)
    transit: list[tuple[int, str, int, str, str, int]] = []
    holding = entered = exited = 0
    snapshots: list[ProfileSnapshot] = []
    peak_queue = delay = overloaded_intervals = 0
    bottleneck_node: str | None = None
    peak_utilization = 0.0
    clearance: int | None = None

    for minute in times:
        incoming = {node_id: 0 for node_id in node_ids}
        served = {node_id: 0 for node_id in node_ids}
        departing = {node_id: 0 for node_id in node_ids}
        remaining: list[tuple[int, str, int, str, str, int]] = []
        for arrival, node_id, direction, final_node, edge_id, count in transit:
            if arrival <= minute:
                queues[node_id, direction, final_node] += count
                incoming[node_id] += count
            else:
                remaining.append((arrival, node_id, direction, final_node, edge_id, count))
        transit = remaining

        # Inbound road/shuttle passengers are explicit direct-access arrivals;
        # rail/walk passengers enter the configured physical corridor.
        for row in demand_at[minute, "inbound"]:
            count = int(row["passenger_demand"])
            mode = row["mode"]
            if mode in {"road", "shuttle"}:
                queues["stadium", 1, "stadium"] += count
                incoming["stadium"] += count
            else:
                origin = row["origin_node"]
                queues[origin, 1, "stadium"] += count
                incoming[origin] += count
            entered += count

        # Stadium admission only occurs after the configured gate marker.
        if minute >= gates:
            for key in [key for key in queues if key[0] == "stadium" and key[1] == 1 and key[2] == "stadium"]:
                count = queues.pop(key)
                holding += count
                served["stadium"] += count

        # Outbound profile rows request release from holding, not new people.
        for row in sorted(demand_at[minute, "outbound"], key=lambda item: (item["mode"], item["destination_node"])):
            requested = int(row["passenger_demand"])
            count = min(holding, requested)
            holding -= count
            if row["mode"] in {"road", "shuttle"}:
                exited += count
                served["stadium"] += count
                departing["stadium"] += count
            else:
                queues["stadium", -1, row["destination_node"]] += count

        # People have completed a network journey when their destination node is reached.
        for key in [key for key in queues if key[1] == -1 and key[0] == key[2]]:
            node_id, _, _ = key
            count = queues.pop(key)
            exited += count
            served[node_id] += count
            departing[node_id] += count

        edge_flows: dict[str, list[int]] = {edge.edge_id: [0, capacity_at[minute, edge.edge_id], 0] for edge in config.edges}
        node_capacities = {node_id: 0 for node_id in node_ids}
        waits: dict[str, list[float | None]] = {node_id: [] for node_id in node_ids}
        for (node_id, direction, final_node), requested in sorted(list(queues.items())):
            if not requested:
                continue
            if direction == 1 and node_id == final_node:
                waits[node_id].append(float(max(0, gates - minute)))
                continue
            index = node_index[node_id]
            next_index = index + direction
            if not 0 <= next_index < len(nodes):
                raise ValueError("Profile passenger has no valid next corridor node")
            edge = edge_by_pair[node_id, nodes[next_index].node_id]
            edge_flows[edge.edge_id][0] += requested
        for (node_id, direction, final_node), requested in sorted(list(queues.items())):
            if not requested:
                continue
            if direction == 1 and node_id == final_node:
                continue
            index = node_index[node_id]
            edge = edge_by_pair[node_id, nodes[index + direction].node_id]
            capacity = edge_flows[edge.edge_id][1]
            available = capacity - edge_flows[edge.edge_id][2]
            count = min(requested, max(0, available))
            queues[node_id, direction, final_node] -= count
            served[node_id] += count
            departing[node_id] += count
            node_capacities[node_id] += capacity
            if count:
                transit.append((minute + travel_minutes[edge.edge_id], edge.to_node, direction, final_node, edge.edge_id, count))
                edge_flows[edge.edge_id][2] += count
            backlog = queues[node_id, direction, final_node]
            if backlog:
                waits[node_id].append(ceil(backlog / capacity) * dt if capacity else None)

        edge_states = tuple(
            ProfileEdgeState(edge_id=edge.edge_id, demand=edge_flows[edge.edge_id][0],
                             capacity=edge_flows[edge.edge_id][1], throughput=edge_flows[edge.edge_id][2],
                             utilization=edge_flows[edge.edge_id][2] / edge_flows[edge.edge_id][1] if edge_flows[edge.edge_id][1] else 0.0,
                             in_transit_passengers=sum(batch[5] for batch in transit if batch[4] == edge.edge_id))
            for edge in config.edges
        )
        terminal_nodes = {"stadium"} if served["stadium"] and minute >= gates else set()
        node_states = tuple(
            ProfileNodeState(node_id=node_id, incoming_passengers=incoming[node_id],
                             queue_passengers=sum(value for (queued_node, _, _), value in queues.items() if queued_node == node_id),
                             served_passengers=served[node_id], departing_passengers=departing[node_id],
                             utilization=None if node_id in terminal_nodes else (
                                 served[node_id] / node_capacities[node_id] if node_capacities[node_id] else 0.0
                             ),
                             estimated_wait_minutes=None if None in waits[node_id] else max(waits[node_id], default=0.0),
                             holding_passengers=holding if node_id == "stadium" else 0)
            for node_id in node_ids
        )
        inventory = sum(node.queue_passengers + node.holding_passengers for node in node_states)
        inventory += sum(edge.in_transit_passengers for edge in edge_states)
        if inventory != entered - exited or any(node.queue_passengers < 0 for node in node_states):
            raise ValueError("Profile replay does not conserve passengers")
        if any(edge.throughput > min(edge.demand, edge.capacity) for edge in edge_states):
            raise ValueError("Profile replay exceeds edge capacity or demand")
        snapshot = ProfileSnapshot(selected, timestamp_at[minute], minute, phase_at[minute], node_states, edge_states,
                                   entered, inventory, exited)
        snapshots.append(snapshot)
        total_queue = sum(node.queue_passengers for node in node_states)
        if total_queue > peak_queue:
            peak_queue = total_queue
            bottleneck_node = max(node_states, key=lambda node: node.queue_passengers).node_id if total_queue else None
        delay += total_queue * dt
        overloaded_intervals += int(any(edge.demand > edge.capacity for edge in edge_states))
        peak_utilization = max(peak_utilization, *(edge.utilization for edge in edge_states))
        if clearance is None and minute >= whistle and exited == entered and entered:
            clearance = minute - whistle

    return ProfileMobilityRun(tuple(snapshots), peak_queue, bottleneck_node, delay,
                              overloaded_intervals, clearance, peak_utilization,
                              entered, exited, exited == entered)
