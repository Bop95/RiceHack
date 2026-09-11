"""Generate deterministic synthetic mobility/access inputs for FinalFlow.

These files are scenario assumptions for a demonstration, not observed World Cup
operations. Queues, waits, utilization, clearance, emissions totals, and
recommendations are intentionally not produced here.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import sys
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Iterable

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
if str(REPOSITORY_ROOT) not in sys.path:
    sys.path.insert(0, str(REPOSITORY_ROOT))

from paddydash.services.mobility_config import default_mobility_config


SEED = 2026
SCHEMA_VERSION = "1.0.0"
GENERATOR_VERSION = "1.0.0"
DEMONSTRATION_START = datetime(2026, 7, 19, 15, tzinfo=timezone.utc)
START_MINUTE, END_MINUTE = -180, 315
ACCESS_ZONES = (
    ("midtown_access", "over_1600m"),
    ("penn_station_access", "800m_to_1600m"),
    ("secaucus_transfer", "400m_to_800m"),
    ("meadowlands_access", "400m_to_800m"),
    ("stadium_egress", "under_400m"),
)
PARKING_ZONES = (
    ("stadium_parking", 2_000),
    ("meadowlands_remote", 1_200),
    ("secaucus_park_ride", 1_000),
    ("midtown_park_ride", 800),
)
PEDESTRIAN_SEGMENTS = (
    ("midtown_penn_walk", "midtown_access", "penn_station_access", 7.0),
    ("penn_concourse", "penn_station_access", "penn_station_access", 9.0),
    ("secaucus_transfer", "secaucus_transfer", "secaucus_transfer", 8.0),
    ("meadowlands_platform", "meadowlands_access", "meadowlands_access", 6.0),
    ("meadowlands_stadium_walk", "meadowlands_access", "stadium_egress", 8.0),
    ("stadium_egress_walk", "stadium_egress", "meadowlands_access", 10.0),
)
MODE_SHARES = {
    "baseline": {"rail": 0.45, "walk": 0.15, "shuttle": 0.10, "road": 0.30},
    "rail_disruption": {"rail": 0.45, "walk": 0.15, "shuttle": 0.10, "road": 0.30},
    "rail_capacity_boost": {"rail": 0.45, "walk": 0.15, "shuttle": 0.10, "road": 0.30},
    "rain": {"rail": 0.45, "walk": 0.08, "shuttle": 0.17, "road": 0.30},
    "staggered_departure": {"rail": 0.45, "walk": 0.15, "shuttle": 0.10, "road": 0.30},
}
ORIGIN_SHARES = {"midtown": 0.65, "penn_station": 0.15, "secaucus": 0.12, "meadowlands": 0.08}
ZONE_WEIGHTS = {"midtown_access": 0.35, "penn_station_access": 0.20,
                "secaucus_transfer": 0.15, "meadowlands_access": 0.15,
                "stadium_egress": 0.15}


FIELDS = {
    "matchday_passenger_demand.csv": [
        "scenario_id", "timestamp", "time_minutes", "phase_id", "origin_node",
        "destination_node", "mode", "direction", "passenger_demand", "mode_share",
        "demand_multiplier", "source_profile", "data_type", "confidence_type",
        "assumption_note",
    ],
    "transit_service_capacity.csv": [
        "scenario_id", "timestamp", "time_minutes", "phase_id", "edge_id", "from_node",
        "to_node", "mode", "scheduled_capacity", "effective_capacity",
        "service_frequency_minutes", "disruption_factor", "weather_factor", "data_type",
        "confidence_type", "assumption_note",
    ],
    "first_last_mile_demand.csv": [
        "scenario_id", "timestamp", "time_minutes", "phase_id", "zone_id", "access_mode",
        "arriving_passengers", "departing_passengers", "distance_band", "walking_pressure",
        "data_type", "confidence_type", "assumption_note",
    ],
    "road_access_demand.csv": [
        "scenario_id", "timestamp", "time_minutes", "phase_id", "zone_id", "vehicle_mode",
        "vehicle_count", "average_occupancy", "passenger_count", "pickup_dropoff_demand",
        "road_capacity_index", "data_type", "confidence_type", "assumption_note",
    ],
    "parking_demand.csv": [
        "scenario_id", "timestamp", "time_minutes", "phase_id", "parking_zone_id",
        "estimated_spaces", "occupied_spaces_input", "arrival_vehicles", "departure_vehicles",
        "average_vehicle_occupancy", "data_type", "confidence_type", "assumption_note",
    ],
    "pedestrian_demand.csv": [
        "scenario_id", "timestamp", "time_minutes", "phase_id", "segment_id", "from_zone",
        "to_zone", "pedestrian_demand", "effective_width_m", "walking_speed_mps",
        "effective_capacity_per_interval", "weather_factor", "data_type", "confidence_type",
        "assumption_note",
    ],
    "interventions.csv": [
        "intervention_id", "name", "category", "target_id", "capacity_change_pct",
        "demand_shift_pct", "departure_spread_minutes", "implementation_cost_band",
        "description", "data_type", "confidence_type", "assumption_note",
    ],
    "emissions_factors.csv": [
        "mode", "emissions_kg_co2e_per_passenger_km", "average_occupancy", "source_type",
        "data_type", "confidence_type", "assumption_note",
    ],
    "corridor_reference.csv": [
        "node_id", "display_name", "order", "latitude", "longitude", "node_type",
        "data_type", "confidence_type", "assumption_note",
    ],
    "zone_reference.csv": [
        "zone_id", "zone_name", "zone_type", "associated_node", "latitude", "longitude",
        "data_type", "confidence_type", "assumption_note",
    ],
}
PRIMARY_IDENTIFIERS = {
    "matchday_passenger_demand.csv": ("scenario_id", "timestamp", "time_minutes", "phase_id", "origin_node", "destination_node", "mode", "direction"),
    "transit_service_capacity.csv": ("scenario_id", "timestamp", "time_minutes", "phase_id", "edge_id", "from_node", "to_node", "mode"),
    "first_last_mile_demand.csv": ("scenario_id", "timestamp", "time_minutes", "phase_id", "zone_id", "access_mode"),
    "road_access_demand.csv": ("scenario_id", "timestamp", "time_minutes", "phase_id", "zone_id", "vehicle_mode"),
    "parking_demand.csv": ("scenario_id", "timestamp", "time_minutes", "phase_id", "parking_zone_id"),
    "pedestrian_demand.csv": ("scenario_id", "timestamp", "time_minutes", "phase_id", "segment_id", "from_zone", "to_zone"),
    "interventions.csv": ("intervention_id",),
    "emissions_factors.csv": ("mode",),
    "corridor_reference.csv": ("node_id",),
    "zone_reference.csv": ("zone_id",),
}
ASSUMPTION_NOTE = "Synthetic scenario assumption for FinalFlow demonstration; not observed event operations."


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=Path("data/synthetic"))
    parser.add_argument("--seed", type=int, default=SEED)
    parser.add_argument("--overwrite", action="store_true")
    return parser.parse_args(argv)


def timestamp_for(minute: int) -> str:
    return (DEMONSTRATION_START + timedelta(minutes=minute)).isoformat().replace("+00:00", "Z")


def phase_for(minute: int, config: Any) -> str:
    events = {phase.start_minute: phase.phase_id.value for phase in config.phases if phase.kind == "event"}
    if minute in events:
        return events[minute]
    intervals = [phase for phase in config.phases if phase.kind == "interval" and phase.start_minute <= minute]
    return max(intervals, key=lambda phase: phase.start_minute).phase_id.value


def allocate(total: int, weights: dict[str, float]) -> dict[str, int]:
    """Deterministically allocate an integer total while conserving every person."""
    keys = list(weights)
    weight_sum = sum(weights.values())
    if weight_sum <= 0:
        raise ValueError("Allocation weights must have a positive sum")
    normalized = {key: weights[key] / weight_sum for key in keys}
    values = {key: int(total * normalized[key]) for key in keys}
    remainder = total - sum(values.values())
    ranked = sorted(keys, key=lambda key: (-(total * normalized[key] - values[key]), key))
    for key in ranked[:remainder]:
        values[key] += 1
    return values


def inbound_profile(minute: int, config: Any) -> int:
    if not config.demand.arrival_start_minute <= minute < config.demand.arrival_end_minute:
        return 0
    index = (minute - config.demand.arrival_start_minute) // config.time_step_minutes
    weights = [1, 1, 1, 2, 2, 3, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 16, 15, 14, 12]
    return allocate(config.demand.cohort_size, {str(i): weight for i, weight in enumerate(weights)})[str(index)]


def outbound_profile(minute: int, scenario_id: str, config: Any) -> int:
    if minute < 135:
        return 0
    baseline_steps = config.demand.departure_duration_minutes // config.time_step_minutes
    steps = baseline_steps * (2 if scenario_id == "staggered_departure" else 1)
    index = (minute - 135) // config.time_step_minutes
    if index >= steps:
        return 0
    if scenario_id == "staggered_departure":
        weights = [2 + min(i, 11) for i in range(steps)]
    else:
        weights = [16 - min(i, 11) for i in range(steps)]
    return allocate(config.demand.cohort_size, {str(i): weight for i, weight in enumerate(weights)})[str(index)]


def base_rows(scenario_id: str, minute: int, config: Any) -> dict[str, Any]:
    return {"scenario_id": scenario_id, "timestamp": timestamp_for(minute), "time_minutes": minute,
            "phase_id": phase_for(minute, config), "data_type": "synthetic",
            "confidence_type": "scenario", "assumption_note": ASSUMPTION_NOTE}


def generate_passenger_demand(config: Any) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    baseline: dict[tuple[int, str, str, str], int] = {}
    for scenario in config.scenarios:
        scenario_id = scenario.scenario_id.value
        for minute in range(START_MINUTE, END_MINUTE + 1, config.time_step_minutes):
            for direction, total in (("inbound", inbound_profile(minute, config)),
                                     ("outbound", outbound_profile(minute, scenario_id, config))):
                by_origin = allocate(total, ORIGIN_SHARES)
                for node, node_total in by_origin.items():
                    origin, destination = (node, "stadium") if direction == "inbound" else ("stadium", node)
                    mode_shares = mode_shares_for(scenario_id, direction, minute)
                    by_mode = allocate(node_total, mode_shares)
                    for mode, people in by_mode.items():
                        key = (minute, direction, node, mode)
                        if scenario_id == "baseline":
                            baseline[key] = people
                        reference = baseline.get(key, people)
                        multiplier = 1.0 if reference == 0 else round(people / reference, 4)
                        row = base_rows(scenario_id, minute, config)
                        row.update({"origin_node": origin, "destination_node": destination, "mode": mode,
                                    "direction": direction, "passenger_demand": people,
                                    "mode_share": mode_shares[mode],
                                    "demand_multiplier": multiplier,
                                    "source_profile": "staggered_outbound_v1" if scenario_id == "staggered_departure" and direction == "outbound" else "matchday_profile_v1"})
                        rows.append(row)
    return rows


def factors(scenario_id: str, mode: str) -> tuple[float, float]:
    disruption = 0.5 if scenario_id == "rail_disruption" and mode == "rail" else 1.0
    if scenario_id == "rail_capacity_boost" and mode == "rail":
        disruption = 1.5
    weather = 0.8 if scenario_id == "rain" and mode in {"walk", "rail"} else 1.0
    return disruption, weather


def mode_shares_for(scenario_id: str, direction: str, minute: int) -> dict[str, float]:
    """Return documented shares, including a short final-whistle rail surge."""
    if direction == "outbound" and 135 <= minute <= 140:
        if scenario_id == "rain":
            return {"rail": 0.65, "walk": 0.04, "shuttle": 0.19, "road": 0.12}
        return {"rail": 0.80, "walk": 0.07, "shuttle": 0.06, "road": 0.07}
    return MODE_SHARES[scenario_id]


def generate_capacity(config: Any) -> list[dict[str, Any]]:
    rows = []
    for scenario in config.scenarios:
        for minute in range(START_MINUTE, END_MINUTE + 1, config.time_step_minutes):
            for edge in config.edges:
                disruption, weather = factors(scenario.scenario_id.value, edge.mode)
                row = base_rows(scenario.scenario_id.value, minute, config)
                scheduled = edge.base_capacity_per_step
                row.update({"edge_id": edge.edge_id, "from_node": edge.from_node, "to_node": edge.to_node,
                            "mode": edge.mode, "scheduled_capacity": scheduled,
                            "effective_capacity": int(scheduled * disruption * weather),
                            "service_frequency_minutes": config.time_step_minutes if edge.mode == "rail" else 0,
                            "disruption_factor": disruption, "weather_factor": weather})
                rows.append(row)
    return rows


def totals_by_mode(rows: Iterable[dict[str, Any]]) -> dict[tuple[str, int, str, str], int]:
    totals: dict[tuple[str, int, str, str], int] = defaultdict(int)
    for row in rows:
        totals[row["scenario_id"], int(row["time_minutes"]), row["direction"], row["mode"]] += int(row["passenger_demand"])
    return totals


def generate_first_last_mile(config: Any, passenger_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    totals = totals_by_mode(passenger_rows)
    rows = []
    for scenario in config.scenarios:
        scenario_id = scenario.scenario_id.value
        for minute in range(START_MINUTE, END_MINUTE + 1, config.time_step_minutes):
            for mode in ("rail", "walk", "shuttle", "road"):
                arriving = allocate(totals[scenario_id, minute, "inbound", mode], ZONE_WEIGHTS)
                departing = allocate(totals[scenario_id, minute, "outbound", mode], ZONE_WEIGHTS)
                for zone_id, distance_band in ACCESS_ZONES:
                    value = max(arriving[zone_id], departing[zone_id])
                    row = base_rows(scenario_id, minute, config)
                    row.update({"zone_id": zone_id, "access_mode": mode,
                                "arriving_passengers": arriving[zone_id], "departing_passengers": departing[zone_id],
                                "distance_band": distance_band,
                                "walking_pressure": "high" if value >= 80 else "medium" if value >= 20 else "low"})
                    rows.append(row)
    return rows


def generate_road_access(config: Any, passenger_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    totals = totals_by_mode(passenger_rows)
    occupancies = {"private_vehicle": 2.0, "rideshare": 1.5, "shuttle": 20.0}
    splits = {"private_vehicle": 0.7, "rideshare": 0.3, "shuttle": 1.0}
    rows = []
    for scenario in config.scenarios:
        scenario_id = scenario.scenario_id.value
        for minute in range(START_MINUTE, END_MINUTE + 1, config.time_step_minutes):
            for vehicle_mode in occupancies:
                source_mode = "shuttle" if vehicle_mode == "shuttle" else "road"
                people = totals[scenario_id, minute, "inbound", source_mode] + totals[scenario_id, minute, "outbound", source_mode]
                for zone_id, _ in ACCESS_ZONES:
                    allocation = allocate(round(people * splits[vehicle_mode]), ZONE_WEIGHTS)[zone_id]
                    vehicles = round(allocation / occupancies[vehicle_mode])
                    passenger_count = round(vehicles * occupancies[vehicle_mode])
                    row = base_rows(scenario_id, minute, config)
                    row.update({"zone_id": zone_id, "vehicle_mode": vehicle_mode, "vehicle_count": vehicles,
                                "average_occupancy": occupancies[vehicle_mode], "passenger_count": passenger_count,
                                "pickup_dropoff_demand": vehicles if vehicle_mode == "rideshare" else 0,
                                "road_capacity_index": 0.65 if scenario_id == "rain" else 0.75})
                    rows.append(row)
    return rows


def generate_parking(config: Any, road_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    private_by_time: dict[tuple[str, int], int] = defaultdict(int)
    for row in road_rows:
        if row["vehicle_mode"] == "private_vehicle":
            private_by_time[row["scenario_id"], int(row["time_minutes"])] += int(row["vehicle_count"])
    parking_weights = {zone: spaces / sum(item[1] for item in PARKING_ZONES) for zone, spaces in PARKING_ZONES}
    rows = []
    for scenario in config.scenarios:
        occupied = {zone: int(spaces * 0.2) for zone, spaces in PARKING_ZONES}
        for minute in range(START_MINUTE, END_MINUTE + 1, config.time_step_minutes):
            arrivals_total = private_by_time[scenario.scenario_id.value, minute] if minute < 135 else 0
            departures_total = private_by_time[scenario.scenario_id.value, minute] if minute >= 135 else 0
            arrivals, departures = allocate(arrivals_total, parking_weights), allocate(departures_total, parking_weights)
            for zone, spaces in PARKING_ZONES:
                arrival = min(arrivals[zone], spaces - occupied[zone])
                departure = min(departures[zone], occupied[zone] + arrival)
                occupied[zone] += arrival - departure
                row = base_rows(scenario.scenario_id.value, minute, config)
                row.update({"parking_zone_id": zone, "estimated_spaces": spaces,
                            "occupied_spaces_input": occupied[zone], "arrival_vehicles": arrival,
                            "departure_vehicles": departure, "average_vehicle_occupancy": 2.0})
                rows.append(row)
    return rows


def generate_pedestrians(config: Any, passenger_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    totals = totals_by_mode(passenger_rows)
    rows = []
    for scenario in config.scenarios:
        scenario_id = scenario.scenario_id.value
        weather = 0.8 if scenario_id == "rain" else 1.0
        speed = 1.04 if scenario_id == "rain" else 1.3
        for minute in range(START_MINUTE, END_MINUTE + 1, config.time_step_minutes):
            people = totals[scenario_id, minute, "inbound", "walk"] + totals[scenario_id, minute, "outbound", "walk"]
            for segment_id, from_zone, to_zone, width in PEDESTRIAN_SEGMENTS:
                row = base_rows(scenario_id, minute, config)
                row.update({"segment_id": segment_id, "from_zone": from_zone, "to_zone": to_zone,
                            "pedestrian_demand": people, "effective_width_m": width,
                            "walking_speed_mps": speed,
                            "effective_capacity_per_interval": int(width * speed * 300 * 0.35 * weather),
                            "weather_factor": weather})
                rows.append(row)
    return rows


def interventions() -> list[dict[str, Any]]:
    items = [
        ("rail_capacity_15", "15% rail capacity boost", "capacity", "rail_edges", .15, 0, 0, "medium"),
        ("rail_capacity_30", "30% rail capacity boost", "capacity", "rail_edges", .30, 0, 0, "high"),
        ("rail_capacity_50", "50% rail capacity boost", "capacity", "rail_edges", .50, 0, 0, "high"),
        ("post_match_shuttle", "Additional post-match shuttle", "service", "stadium_egress", .20, 0, 0, "medium"),
        ("rideshare_geofence", "Rideshare geofencing", "demand_management", "stadium_egress", 0, -.10, 0, "low"),
        ("staggered_departure", "Staggered departure messaging", "departure_management", "stadium", 0, 0, 60, "low"),
        ("commercial_dwell", "Commercial dwell incentive", "departure_management", "stadium_egress", 0, 0, 30, "medium"),
        ("pedestrian_only", "Pedestrian-only corridor", "pedestrian", "meadowlands_stadium_walk", .15, 0, 0, "medium"),
        ("wayfinding", "Additional wayfinding", "pedestrian", "secaucus_transfer", .05, 0, 0, "low"),
        ("shaded_queue", "Temporary shaded queue", "weather_resilience", "stadium_egress", 0, 0, 0, "medium"),
        ("covered_transfer", "Covered transfer area", "weather_resilience", "meadowlands_platform", 0, 0, 0, "high"),
        ("platform_management", "Platform management", "operations", "meadowlands", .10, 0, 0, "medium"),
        ("parking_reservation", "Parking reservation messaging", "parking", "stadium_parking", 0, -.05, 0, "low"),
    ]
    return [{"intervention_id": item[0], "name": item[1], "category": item[2], "target_id": item[3],
             "capacity_change_pct": item[4], "demand_shift_pct": item[5], "departure_spread_minutes": item[6],
             "implementation_cost_band": item[7], "description": "Synthetic intervention catalog entry; effect requires a separate deterministic scenario transformation.",
             "data_type": "synthetic", "confidence_type": "scenario", "assumption_note": ASSUMPTION_NOTE} for item in items]


def emissions_factors() -> list[dict[str, Any]]:
    return [{"mode": mode, "emissions_kg_co2e_per_passenger_km": factor, "average_occupancy": occupancy,
             "source_type": "synthetic_assumption", "data_type": "synthetic", "confidence_type": "scenario",
             "assumption_note": "Synthetic placeholder factor; not EPA-validated or an emissions estimate."}
            for mode, factor, occupancy in (("rail", .06, 1.0), ("walk", 0.0, 1.0), ("shuttle", .12, 20.0),
                                             ("rideshare", .22, 1.5), ("private_vehicle", .20, 2.0))]


def corridor_reference(config: Any) -> list[dict[str, Any]]:
    """Return approximate synthetic map points for the configured corridor only."""
    coordinates = {
        "midtown": (40.7549, -73.9840),
        "penn_station": (40.7506, -73.9935),
        "secaucus": (40.7614, -74.0755),
        "meadowlands": (40.8135, -74.0745),
        "stadium": (40.8130, -74.0740),
    }
    return [{
        "node_id": node.node_id, "display_name": node.name, "order": node.order,
        "latitude": coordinates[node.node_id][0], "longitude": coordinates[node.node_id][1],
        "node_type": node.node_type, "data_type": "synthetic", "confidence_type": "scenario",
        "assumption_note": "Approximate synthetic map point for FinalFlow demonstration; not an official access coordinate.",
    } for node in config.nodes]


def zone_reference(config: Any) -> list[dict[str, Any]]:
    """Return the bounded synthetic access zones used by first/last-mile inputs."""
    node_points = {row["node_id"]: row for row in corridor_reference(config)}
    associations = {
        "midtown_access": ("Midtown access", "access", "midtown"),
        "penn_station_access": ("Penn Station access", "access", "penn_station"),
        "secaucus_transfer": ("Secaucus transfer", "transfer", "secaucus"),
        "meadowlands_access": ("Meadowlands access", "access", "meadowlands"),
        "stadium_egress": ("Stadium egress", "egress", "stadium"),
    }
    return [{
        "zone_id": zone_id, "zone_name": name, "zone_type": zone_type,
        "associated_node": node_id, "latitude": node_points[node_id]["latitude"],
        "longitude": node_points[node_id]["longitude"], "data_type": "synthetic",
        "confidence_type": "scenario",
        "assumption_note": "Synthetic analysis zone anchored to an approximate demonstration map point; not an official boundary.",
    } for zone_id, (name, zone_type, node_id) in associations.items()]


def validate(datasets: dict[str, list[dict[str, Any]]], config: Any) -> None:
    scenarios = {item.scenario_id.value for item in config.scenarios}
    phases = {item.phase_id.value for item in config.phases}
    nodes = {item.node_id for item in config.nodes}
    edges = {item.edge_id for item in config.edges}
    for filename, rows in datasets.items():
        if not rows or set(rows[0]) != set(FIELDS[filename]):
            raise ValueError(f"{filename} has an invalid schema")
        for row in rows:
            if row["data_type"] != "synthetic" or row["confidence_type"] != "scenario":
                raise ValueError(f"{filename} has invalid provenance")
            for key in PRIMARY_IDENTIFIERS[filename]:
                if not str(row.get(key, "")).strip():
                    raise ValueError(f"{filename} has a missing primary identifier")
            if filename not in {"interventions.csv", "emissions_factors.csv", "corridor_reference.csv", "zone_reference.csv"}:
                if row["scenario_id"] not in scenarios or row["phase_id"] not in phases:
                    raise ValueError(f"{filename} has an unknown scenario or phase")
                if int(row["time_minutes"]) % config.time_step_minutes:
                    raise ValueError(f"{filename} has a misaligned timestamp")
            if any(float(value) < 0 for key, value in row.items() if key in {"passenger_demand", "scheduled_capacity", "effective_capacity", "arriving_passengers", "departing_passengers", "vehicle_count", "passenger_count", "estimated_spaces", "occupied_spaces_input", "arrival_vehicles", "departure_vehicles", "pedestrian_demand", "effective_width_m", "walking_speed_mps", "effective_capacity_per_interval"}):
                raise ValueError(f"{filename} has a negative count or capacity")
    demand = datasets["matchday_passenger_demand.csv"]
    shares: dict[tuple[str, int, str, str], float] = defaultdict(float)
    for row in demand:
        if row["origin_node"] not in nodes or row["destination_node"] not in nodes:
            raise ValueError("Passenger demand has an unknown node")
        access_node = row["origin_node"] if row["direction"] == "inbound" else row["destination_node"]
        shares[row["scenario_id"], int(row["time_minutes"]), row["direction"], access_node] += float(row["mode_share"])
    if any(abs(value - 1.0) > 1e-9 for value in shares.values()):
        raise ValueError("Passenger mode shares must sum to one")
    if any(row["edge_id"] not in edges for row in datasets["transit_service_capacity.csv"]):
        raise ValueError("Capacity has an unknown edge")
    edge_lookup = {edge.edge_id: edge for edge in config.edges}
    for row in datasets["transit_service_capacity.csv"]:
        edge = edge_lookup[row["edge_id"]]
        if (row["from_node"], row["to_node"], row["mode"]) != (edge.from_node, edge.to_node, edge.mode):
            raise ValueError("Capacity edge metadata does not match the configured edge")
        expected = int(float(row["scheduled_capacity"]) * float(row["disruption_factor"]) * float(row["weather_factor"]))
        if int(row["effective_capacity"]) != expected:
            raise ValueError("Capacity factors do not match effective capacity")
    for row in datasets["road_access_demand.csv"]:
        if int(row["passenger_count"]) != round(int(row["vehicle_count"]) * float(row["average_occupancy"])):
            raise ValueError("Road passenger count does not match occupancy")
    if {row["node_id"] for row in datasets["corridor_reference.csv"]} != nodes:
        raise ValueError("Corridor reference does not match configured nodes")
    if any(row["associated_node"] not in nodes for row in datasets["zone_reference.csv"]):
        raise ValueError("Zone reference has an unknown associated node")
    by_zone: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for row in datasets["parking_demand.csv"]:
        if int(row["occupied_spaces_input"]) > int(row["estimated_spaces"]):
            raise ValueError("Parking occupancy exceeds synthetic capacity")
        by_zone[row["scenario_id"], row["parking_zone_id"]].append(row)
    for rows in by_zone.values():
        rows.sort(key=lambda row: int(row["time_minutes"]))
        for previous, current in zip(rows, rows[1:]):
            if int(current["occupied_spaces_input"]) != int(previous["occupied_spaces_input"]) + int(current["arrival_vehicles"]) - int(current["departure_vehicles"]):
                raise ValueError("Parking occupancy is not balanced")


def write_csv(path: Path, rows: list[dict[str, Any]], overwrite: bool) -> None:
    if path.exists() and not overwrite:
        raise FileExistsError(f"Refusing to overwrite {path}; use --overwrite")
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=FIELDS[path.name], lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run(args: argparse.Namespace) -> dict[str, Any]:
    if args.seed != SEED:
        raise ValueError(f"This version supports the documented fixed seed only: {SEED}")
    config = default_mobility_config()
    demand = generate_passenger_demand(config)
    datasets = {
        "matchday_passenger_demand.csv": demand,
        "transit_service_capacity.csv": generate_capacity(config),
        "first_last_mile_demand.csv": generate_first_last_mile(config, demand),
        "road_access_demand.csv": generate_road_access(config, demand),
    }
    datasets["parking_demand.csv"] = generate_parking(config, datasets["road_access_demand.csv"])
    datasets["pedestrian_demand.csv"] = generate_pedestrians(config, demand)
    datasets["interventions.csv"] = interventions()
    datasets["emissions_factors.csv"] = emissions_factors()
    datasets["corridor_reference.csv"] = corridor_reference(config)
    datasets["zone_reference.csv"] = zone_reference(config)
    validate(datasets, config)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    paths = {}
    for filename, rows in datasets.items():
        path = args.output_dir / filename
        write_csv(path, rows, args.overwrite)
        paths[filename] = {"rows": len(rows), "sha256": sha256(path)}
    manifest_path = args.output_dir / "manifest.json"
    if manifest_path.exists() and not args.overwrite:
        raise FileExistsError(f"Refusing to overwrite {manifest_path}; use --overwrite")
    manifest = {
        "schema_version": SCHEMA_VERSION, "generator_version": GENERATOR_VERSION,
        "random_seed": args.seed, "generated_at": DEMONSTRATION_START.isoformat().replace("+00:00", "Z"),
        "config_id": config.config_id, "datasets": paths, "row_counts": {name: item["rows"] for name, item in paths.items()},
        "scenario_ids": [item.scenario_id.value for item in config.scenarios],
        "phase_ids": [item.phase_id.value for item in config.phases],
        "timeline": {"start_time_minutes": START_MINUTE, "end_time_minutes": END_MINUTE, "time_step_minutes": config.time_step_minutes, "demonstration_start": DEMONSTRATION_START.isoformat().replace("+00:00", "Z")},
        "source_references": ["paddydash/services/mobility_config.py", "docs/data/synthetic-data-plan.md"],
        "assumptions": list(config.assumptions),
        "provenance": {"data_type": "synthetic", "confidence_type": "scenario", "statement": ASSUMPTION_NOTE},
    }
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return {"output_dir": str(args.output_dir), "row_counts": manifest["row_counts"], "manifest": str(manifest_path)}


def main() -> int:
    args = parse_args()
    try:
        result = run(args)
    except (FileExistsError, ValueError) as error:
        print(f"ERROR: {error}")
        return 1
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
