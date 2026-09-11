"""Derive FinalFlow mobility outputs from the documented synthetic input profiles.

The script never invents queues, waits, utilization, clearance or recommendations.
All exported values are deterministic replay results and are labelled ``derived``
because their inputs are synthetic scenario assumptions.
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any, Iterable

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
if str(REPOSITORY_ROOT) not in sys.path:
    sys.path.insert(0, str(REPOSITORY_ROOT))

from paddydash.services.mobility_config import default_mobility_config
from paddydash.services.mobility_simulator import ProfileMobilityRun, run_profile_simulation


GENERATOR_VERSION = "1.0.0"
ASSUMPTION_NOTE = (
    "Derived from synthetic FinalFlow scenario inputs; not observed event operations."
)
INPUT_FILES = (
    "matchday_passenger_demand.csv",
    "transit_service_capacity.csv",
    "first_last_mile_demand.csv",
    "road_access_demand.csv",
    "parking_demand.csv",
    "pedestrian_demand.csv",
    "interventions.csv",
    "emissions_factors.csv",
    "manifest.json",
)
OUTPUT_FIELDS = {
    "mobility_node_timeseries.csv": [
        "scenario_id", "timestamp", "time_minutes", "phase_id", "node_id",
        "incoming_passengers", "queue_passengers", "holding_passengers",
        "served_passengers", "departing_passengers", "utilization",
        "estimated_wait_minutes", "data_type", "assumption_note",
    ],
    "mobility_edge_timeseries.csv": [
        "scenario_id", "timestamp", "time_minutes", "phase_id", "edge_id",
        "demand", "capacity", "throughput", "utilization", "in_transit_passengers",
        "data_type", "assumption_note",
    ],
    "scenario_summary.csv": [
        "scenario_id", "peak_queue_passengers", "peak_post_final_whistle_queue_passengers",
        "bottleneck_node", "peak_utilization", "total_clearance_minutes",
        "passenger_delay_proxy_person_minutes", "overloaded_intervals", "total_arrivals",
        "total_departures", "direct_access_arrivals", "peak_queue_improvement_vs_baseline",
        "delay_proxy_improvement_vs_baseline", "data_type", "assumption_note",
    ],
    "mobility_access_summary.csv": [
        "scenario_id", "peak_pedestrian_load_ratio", "peak_parking_utilization",
        "peak_rideshare_passengers", "peak_shuttle_passengers", "rail_passenger_total",
        "walk_passenger_total", "road_passenger_total", "shuttle_passenger_total",
        "shuttle_utilization_status", "data_type", "assumption_note",
    ],
    "intervention_comparison.csv": [
        "intervention_id", "name", "target_id", "comparison_scenario_id",
        "evaluation_status", "baseline_peak_queue_passengers",
        "scenario_peak_queue_passengers", "peak_queue_improvement",
        "baseline_delay_proxy_person_minutes", "scenario_delay_proxy_person_minutes",
        "delay_proxy_improvement", "data_type", "assumption_note",
    ],
}
SCENARIO_INTERVENTION_MAP = {
    "rail_capacity_50": "rail_capacity_boost",
    "staggered_departure": "staggered_departure",
}


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """Parse paths while leaving all source inputs read-only."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input-dir", type=Path, default=Path("data/synthetic"))
    parser.add_argument("--output-dir", type=Path, default=Path("data/exports"))
    parser.add_argument("--overwrite", action="store_true")
    return parser.parse_args(argv)


def read_csv(path: Path) -> list[dict[str, str]]:
    """Read a UTF-8 CSV file with a clear error for missing or malformed input."""
    if not path.is_file():
        raise FileNotFoundError(f"Required input file is missing: {path}")
    try:
        with path.open(newline="", encoding="utf-8") as stream:
            reader = csv.DictReader(stream)
            if reader.fieldnames is None:
                raise ValueError(f"Input file has no header: {path}")
            return list(reader)
    except UnicodeDecodeError as error:
        raise ValueError(f"Input file is not valid UTF-8: {path}") from error
    except csv.Error as error:
        raise ValueError(f"Input file is malformed CSV: {path}") from error


def read_inputs(input_dir: Path) -> dict[str, Any]:
    """Load the generated scenario tables without changing them."""
    if not input_dir.is_dir():
        raise FileNotFoundError(f"Synthetic input directory is missing: {input_dir}")
    tables: dict[str, Any] = {}
    for filename in INPUT_FILES:
        path = input_dir / filename
        if filename.endswith(".json"):
            if not path.is_file():
                raise FileNotFoundError(f"Required input file is missing: {path}")
            tables[filename] = json.loads(path.read_text(encoding="utf-8"))
        else:
            tables[filename] = read_csv(path)
    return tables


def profile_runs(tables: dict[str, Any]) -> dict[str, ProfileMobilityRun]:
    """Run every centrally configured scenario against the input profiles."""
    config = default_mobility_config()
    demand = tables["matchday_passenger_demand.csv"]
    capacity = tables["transit_service_capacity.csv"]
    return {
        scenario.scenario_id.value: run_profile_simulation(
            config, scenario.scenario_id, demand, capacity
        )
        for scenario in config.scenarios
    }


def validate_profile_run(run: ProfileMobilityRun) -> None:
    """Assert replay conservation and edge bounds before exporting any metrics."""
    previous_entered = previous_exited = 0
    for snapshot in run.snapshots:
        if snapshot.total_entered < previous_entered or snapshot.total_exited < previous_exited:
            raise ValueError("Replay totals must be monotonic")
        if snapshot.total_entered != snapshot.total_people_in_system + snapshot.total_exited:
            raise ValueError("Replay passenger conservation failed")
        if snapshot.total_people_in_system < 0:
            raise ValueError("Replay produced a negative passenger inventory")
        for node in snapshot.node_states:
            if node.queue_passengers < 0 or node.holding_passengers < 0:
                raise ValueError("Replay produced a negative queue or holding count")
        for edge in snapshot.edge_states:
            if edge.capacity < 0 or edge.demand < 0 or edge.throughput < 0:
                raise ValueError("Replay produced a negative edge value")
            if edge.throughput > min(edge.capacity, edge.demand):
                raise ValueError("Replay throughput exceeds available demand or capacity")
        previous_entered, previous_exited = snapshot.total_entered, snapshot.total_exited
    if not run.completed or run.total_arrivals != run.total_departures:
        raise ValueError("Replay did not clear its introduced passenger cohort")


def node_rows(runs: dict[str, ProfileMobilityRun]) -> list[dict[str, Any]]:
    """Flatten profile node states at scenario x interval x node grain."""
    rows: list[dict[str, Any]] = []
    for scenario_id, run in runs.items():
        for snapshot in run.snapshots:
            for node in snapshot.node_states:
                rows.append({
                    "scenario_id": scenario_id, "timestamp": snapshot.timestamp,
                    "time_minutes": snapshot.time_minutes, "phase_id": snapshot.phase_id,
                    "node_id": node.node_id, "incoming_passengers": node.incoming_passengers,
                    "queue_passengers": node.queue_passengers,
                    "holding_passengers": node.holding_passengers,
                    "served_passengers": node.served_passengers,
                    "departing_passengers": node.departing_passengers,
                    "utilization": node.utilization,
                    "estimated_wait_minutes": node.estimated_wait_minutes,
                    "data_type": "derived", "assumption_note": ASSUMPTION_NOTE,
                })
    return rows


def edge_rows(runs: dict[str, ProfileMobilityRun]) -> list[dict[str, Any]]:
    """Flatten profile edge states at scenario x interval x edge grain."""
    rows: list[dict[str, Any]] = []
    for scenario_id, run in runs.items():
        for snapshot in run.snapshots:
            for edge in snapshot.edge_states:
                rows.append({
                    "scenario_id": scenario_id, "timestamp": snapshot.timestamp,
                    "time_minutes": snapshot.time_minutes, "phase_id": snapshot.phase_id,
                    "edge_id": edge.edge_id, "demand": edge.demand,
                    "capacity": edge.capacity, "throughput": edge.throughput,
                    "utilization": edge.utilization,
                    "in_transit_passengers": edge.in_transit_passengers,
                    "data_type": "derived", "assumption_note": ASSUMPTION_NOTE,
                })
    return rows


def scenario_rows(
    runs: dict[str, ProfileMobilityRun], tables: dict[str, Any]
) -> list[dict[str, Any]]:
    """Build comparable congestion summaries directly from replay snapshots."""
    baseline = runs["baseline"]
    direct_arrivals: dict[str, int] = defaultdict(int)
    for row in tables["matchday_passenger_demand.csv"]:
        if row["direction"] == "inbound" and row["mode"] in {"road", "shuttle"}:
            direct_arrivals[row["scenario_id"]] += int(row["passenger_demand"])
    rows: list[dict[str, Any]] = []
    for scenario_id, run in runs.items():
        post_final_peak = max(
            sum(node.queue_passengers for node in snapshot.node_states)
            for snapshot in run.snapshots
            if snapshot.time_minutes >= 135
        )
        rows.append({
            "scenario_id": scenario_id, "peak_queue_passengers": run.peak_queue,
            "peak_post_final_whistle_queue_passengers": post_final_peak,
            "bottleneck_node": run.bottleneck_node or "",
            "peak_utilization": run.peak_utilization,
            "total_clearance_minutes": run.clearance_minutes,
            "passenger_delay_proxy_person_minutes": run.delay_person_minutes,
            "overloaded_intervals": run.overloaded_intervals,
            "total_arrivals": run.total_arrivals, "total_departures": run.total_departures,
            "direct_access_arrivals": direct_arrivals[scenario_id],
            "peak_queue_improvement_vs_baseline": baseline.peak_queue - run.peak_queue,
            "delay_proxy_improvement_vs_baseline": baseline.delay_person_minutes - run.delay_person_minutes,
            "data_type": "derived", "assumption_note": ASSUMPTION_NOTE,
        })
    return rows


def access_rows(tables: dict[str, Any], scenario_ids: Iterable[str]) -> list[dict[str, Any]]:
    """Derive bounded access indicators only where matching input denominators exist."""
    pedestrians: dict[str, float] = defaultdict(float)
    parking: dict[str, float] = defaultdict(float)
    rideshare: dict[str, int] = defaultdict(int)
    shuttle_peak: dict[str, int] = defaultdict(int)
    mode_totals: dict[tuple[str, str], int] = defaultdict(int)
    for row in tables["pedestrian_demand.csv"]:
        capacity = int(row["effective_capacity_per_interval"])
        if capacity:
            pedestrians[row["scenario_id"]] = max(
                pedestrians[row["scenario_id"]], int(row["pedestrian_demand"]) / capacity
            )
    for row in tables["parking_demand.csv"]:
        capacity = int(row["estimated_spaces"])
        if capacity:
            parking[row["scenario_id"]] = max(
                parking[row["scenario_id"]], int(row["occupied_spaces_input"]) / capacity
            )
    for row in tables["road_access_demand.csv"]:
        if row["vehicle_mode"] == "rideshare":
            rideshare[row["scenario_id"]] = max(rideshare[row["scenario_id"]], int(row["passenger_count"]))
    for row in tables["first_last_mile_demand.csv"]:
        if row["access_mode"] == "shuttle":
            shuttle_peak[row["scenario_id"]] = max(
                shuttle_peak[row["scenario_id"]],
                int(row["arriving_passengers"]) + int(row["departing_passengers"]),
            )
    for row in tables["matchday_passenger_demand.csv"]:
        mode_totals[row["scenario_id"], row["mode"]] += int(row["passenger_demand"])
    return [{
        "scenario_id": scenario_id,
        "peak_pedestrian_load_ratio": pedestrians[scenario_id],
        "peak_parking_utilization": parking[scenario_id],
        "peak_rideshare_passengers": rideshare[scenario_id],
        "peak_shuttle_passengers": shuttle_peak[scenario_id],
        "rail_passenger_total": mode_totals[scenario_id, "rail"],
        "walk_passenger_total": mode_totals[scenario_id, "walk"],
        "road_passenger_total": mode_totals[scenario_id, "road"],
        "shuttle_passenger_total": mode_totals[scenario_id, "shuttle"],
        "shuttle_utilization_status": "not_derived_no_shuttle_capacity_input",
        "data_type": "derived", "assumption_note": ASSUMPTION_NOTE,
    } for scenario_id in scenario_ids]


def intervention_rows(
    summaries: list[dict[str, Any]], tables: dict[str, Any]
) -> list[dict[str, Any]]:
    """Compare only catalog interventions represented by a deterministic scenario."""
    summary_by_scenario = {row["scenario_id"]: row for row in summaries}
    baseline = summary_by_scenario["baseline"]
    rows: list[dict[str, Any]] = []
    for intervention in tables["interventions.csv"]:
        scenario_id = SCENARIO_INTERVENTION_MAP.get(intervention["intervention_id"], "")
        evaluated = summary_by_scenario.get(scenario_id)
        rows.append({
            "intervention_id": intervention["intervention_id"], "name": intervention["name"],
            "target_id": intervention["target_id"], "comparison_scenario_id": scenario_id,
            "evaluation_status": "modeled" if evaluated else "catalog_only_not_modeled",
            "baseline_peak_queue_passengers": baseline["peak_queue_passengers"] if evaluated else "",
            "scenario_peak_queue_passengers": evaluated["peak_queue_passengers"] if evaluated else "",
            "peak_queue_improvement": evaluated["peak_queue_improvement_vs_baseline"] if evaluated else "",
            "baseline_delay_proxy_person_minutes": baseline["passenger_delay_proxy_person_minutes"] if evaluated else "",
            "scenario_delay_proxy_person_minutes": evaluated["passenger_delay_proxy_person_minutes"] if evaluated else "",
            "delay_proxy_improvement": evaluated["delay_proxy_improvement_vs_baseline"] if evaluated else "",
            "data_type": "derived", "assumption_note": (
                ASSUMPTION_NOTE if evaluated else
                "Catalog entry is synthetic; no matching deterministic scenario transformation exists yet."
            ),
        })
    return rows


def write_csv(path: Path, rows: list[dict[str, Any]], overwrite: bool) -> None:
    """Write a stable UTF-8 CSV only after rejecting accidental overwrite."""
    if path.exists() and not overwrite:
        raise FileExistsError(f"Refusing to overwrite {path}; use --overwrite")
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=OUTPUT_FIELDS[path.name], lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def run(args: argparse.Namespace) -> dict[str, Any]:
    """Derive, validate and export all supported mobility output tables."""
    tables = read_inputs(args.input_dir)
    runs = profile_runs(tables)
    for profile in runs.values():
        validate_profile_run(profile)
    outputs = {
        "mobility_node_timeseries.csv": node_rows(runs),
        "mobility_edge_timeseries.csv": edge_rows(runs),
    }
    outputs["scenario_summary.csv"] = scenario_rows(runs, tables)
    outputs["mobility_access_summary.csv"] = access_rows(tables, runs)
    outputs["intervention_comparison.csv"] = intervention_rows(outputs["scenario_summary.csv"], tables)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    for filename, rows in outputs.items():
        write_csv(args.output_dir / filename, rows, args.overwrite)
    manifest_path = args.output_dir / "mobility_manifest.json"
    if manifest_path.exists() and not args.overwrite:
        raise FileExistsError(f"Refusing to overwrite {manifest_path}; use --overwrite")
    manifest = {
        "schema_version": "1.0.0", "generator_version": GENERATOR_VERSION,
        "generated_at": tables["manifest.json"]["generated_at"],
        "config_id": tables["manifest.json"]["config_id"],
        "input_manifest": "data/synthetic/manifest.json",
        "row_counts": {filename: len(rows) for filename, rows in outputs.items()},
        "scenario_ids": list(runs),
        "provenance": {
            "data_type": "derived", "input_data_type": "synthetic",
            "statement": ASSUMPTION_NOTE,
        },
        "emissions": {
            "status": "not_derived_missing_mode_distance_inputs",
            "reason": "Synthetic emissions factors exist, but no documented mode-distance input exists.",
        },
    }
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return {"output_dir": str(args.output_dir), "row_counts": manifest["row_counts"], "manifest": str(manifest_path)}


def main() -> int:
    """Run the command-line exporter with concise failures for invalid local data."""
    args = parse_args()
    try:
        result = run(args)
    except (FileExistsError, FileNotFoundError, ValueError, json.JSONDecodeError) as error:
        print(f"ERROR: {error}")
        return 1
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
