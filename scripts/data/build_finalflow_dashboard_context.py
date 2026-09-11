"""Build compact, provenance-preserving dashboard context from FinalFlow outputs."""

from __future__ import annotations

import argparse
import csv
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
if str(REPOSITORY_ROOT) not in sys.path:
    sys.path.insert(0, str(REPOSITORY_ROOT))

from paddydash.services.mobility_config import default_mobility_config


ALLOWED_DATA_TYPES = {"provided", "derived", "synthetic", "web"}
GENERATOR_VERSION = "1.0.0"
OUTPUT_FIELDS = {
    "executive_kpis.csv": [
        "kpi_id", "label", "value", "unit", "data_type", "source_data_type",
        "source_file", "limitation",
    ],
    "match_timeline_summary.csv": [
        "phase_id", "display_name", "start_time", "time_minutes", "direction",
        "expected_pressure_level", "data_type", "source_data_type", "assumption_note",
    ],
    "scenario_comparison.csv": [
        "scenario_id", "name", "description", "primary_change", "peak_queue_passengers",
        "peak_post_final_whistle_queue_passengers", "total_clearance_minutes",
        "passenger_delay_proxy_person_minutes", "overloaded_intervals", "data_type",
        "source_data_type", "source_file", "assumption_note",
    ],
    "commercial_context.csv": [
        "context_id", "context_group", "label", "metric_value", "unit", "data_type",
        "source_data_type", "source_file", "limitation",
    ],
    "weather_heat_context.csv": [
        "context_id", "label", "metric_value", "unit", "threshold", "recommended_action",
        "data_type", "source_data_type", "source_file", "limitation",
    ],
    "recommendation_catalog.csv": [
        "condition_id", "metric", "operator", "threshold", "recommendation",
        "evidence_type", "data_type", "assumption_note",
    ],
}
PRIMARY_KEYS = {
    "executive_kpis.csv": ("kpi_id",),
    "match_timeline_summary.csv": ("phase_id",),
    "scenario_comparison.csv": ("scenario_id",),
    "commercial_context.csv": ("context_id",),
    "weather_heat_context.csv": ("context_id",),
    "recommendation_catalog.csv": ("condition_id",),
}


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """Parse read-only source locations and an explicitly protected output path."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--summary-dir", type=Path, default=Path("data/summaries"))
    parser.add_argument("--synthetic-dir", type=Path, default=Path("data/synthetic"))
    parser.add_argument("--mobility-export-dir", type=Path, default=Path("data/exports"))
    parser.add_argument(
        "--business-path", type=Path,
        default=Path("notebooks/duc-anh/data_clean/finalflow_business_integration.csv"),
    )
    parser.add_argument("--output-dir", type=Path, default=Path("data/exports"))
    parser.add_argument("--overwrite", action="store_true")
    return parser.parse_args(argv)


def read_csv(path: Path) -> list[dict[str, str]]:
    """Read a required compact CSV without altering its source data."""
    if not path.is_file():
        raise FileNotFoundError(f"Required source file is missing: {path}")
    with path.open(newline="", encoding="utf-8") as stream:
        reader = csv.DictReader(stream)
        if reader.fieldnames is None:
            raise ValueError(f"Source file has no header: {path}")
        return list(reader)


def primary_change(scenario: Any) -> str:
    """Describe an existing explicit scenario modifier without inventing one."""
    if scenario.capacity_multiplier != 1:
        percent = round((scenario.capacity_multiplier - 1) * 100)
        return f"{percent:+d}% capacity on {', '.join(scenario.affected_modes)}"
    if scenario.travel_time_multiplier != 1:
        percent = round((scenario.travel_time_multiplier - 1) * 100)
        return f"{percent:+d}% travel time on {', '.join(scenario.affected_modes)}"
    if scenario.departure_duration_multiplier != 1:
        return f"{scenario.departure_duration_multiplier:g}x post-match release duration"
    return "Base illustrative demand, capacity, and travel assumptions"


def timeline_rows() -> list[dict[str, Any]]:
    """Materialize canonical match phases from the shared mobility contract."""
    direction_by_phase = {
        "pre_match": ("inbound", "rising"), "gates_open": ("inbound", "rising"),
        "ceremony": ("inbound", "high"), "kickoff": ("match", "low"),
        "first_half": ("match", "low"), "first_half_end": ("match", "low"),
        "halftime": ("local", "moderate"), "second_half": ("match", "low"),
        "regulation_end": ("match", "low"), "extra_time": ("match", "low"),
        "extra_time_end": ("match", "low"), "final_whistle": ("outbound", "high"),
        "post_match": ("outbound", "clearing"),
    }
    return [{
        "phase_id": phase.phase_id.value, "display_name": phase.display_label,
        "start_time": phase.clock_reference, "time_minutes": phase.start_minute,
        "direction": direction_by_phase[phase.phase_id.value][0],
        "expected_pressure_level": direction_by_phase[phase.phase_id.value][1],
        "data_type": "derived", "source_data_type": "synthetic",
        "assumption_note": "Materialized from FinalFlow's illustrative mobility configuration; not an official event schedule.",
    } for phase in default_mobility_config().phases]


def scenario_rows(summaries: list[dict[str, str]]) -> list[dict[str, Any]]:
    """Join deterministic scenario metrics to their configured assumptions."""
    by_id = {row["scenario_id"]: row for row in summaries}
    rows: list[dict[str, Any]] = []
    for scenario in default_mobility_config().scenarios:
        summary = by_id[scenario.scenario_id.value]
        rows.append({
            "scenario_id": scenario.scenario_id.value, "name": scenario.display_label,
            "description": " ".join(scenario.assumptions), "primary_change": primary_change(scenario),
            "peak_queue_passengers": int(summary["peak_queue_passengers"]),
            "peak_post_final_whistle_queue_passengers": int(summary["peak_post_final_whistle_queue_passengers"]),
            "total_clearance_minutes": int(summary["total_clearance_minutes"]),
            "passenger_delay_proxy_person_minutes": int(summary["passenger_delay_proxy_person_minutes"]),
            "overloaded_intervals": int(summary["overloaded_intervals"]),
            "data_type": "derived", "source_data_type": "synthetic",
            "source_file": "scenario_summary.csv; mobility_config.py",
            "assumption_note": "Metrics are deterministic results from synthetic demand and capacity assumptions; not observed operations.",
        })
    return rows


def executive_rows(
    store_summary: dict[str, str], weather: list[dict[str, str]], spatial: list[dict[str, str]],
    scenarios: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Create a small mixed-provenance KPI list, never a merged factual claim."""
    baseline = next(row for row in scenarios if row["scenario_id"] == "baseline")
    weather_by_id = {row["metric_id"]: row for row in weather}
    return [
        {"kpi_id": "baseline_peak_queue", "label": "Baseline peak queue", "value": baseline["peak_queue_passengers"], "unit": "modeled people", "data_type": "derived", "source_data_type": "synthetic", "source_file": "scenario_summary.csv", "limitation": "Derived from synthetic scenario inputs; not observed real-time mobility."},
        {"kpi_id": "baseline_clearance", "label": "Baseline clearance after final whistle", "value": baseline["total_clearance_minutes"], "unit": "modeled minutes", "data_type": "derived", "source_data_type": "synthetic", "source_file": "scenario_summary.csv", "limitation": "Derived from synthetic scenario inputs; not an operational forecast."},
        {"kpi_id": "historical_hot_share", "label": "Historical hot June-July observation share", "value": weather_by_id["summer_hot_observation_share"]["percentage"], "unit": "percent", "data_type": "derived", "source_data_type": "derived", "source_file": "weather_risk_summary.csv", "limitation": weather_by_id["summer_hot_observation_share"]["limitation"]},
        {"kpi_id": "historical_rain_share", "label": "Historical rainy June-July observation share", "value": weather_by_id["summer_rainy_observation_share"]["percentage"], "unit": "percent", "data_type": "derived", "source_data_type": "derived", "source_file": "weather_risk_summary.csv", "limitation": weather_by_id["summer_rainy_observation_share"]["limitation"]},
        {"kpi_id": "reviewed_spatial_locations", "label": "Reviewed exploratory spatial locations", "value": len(spatial), "unit": "locations", "data_type": "derived", "source_data_type": "derived", "source_file": "spatial_heat_locations.csv", "limitation": "Exploratory NY/NJ context; locations are not verified event vendor sites."},
        {"kpi_id": "historical_store_records", "label": "Historical transformed store-day records", "value": int(store_summary["total_rows"]), "unit": "records", "data_type": "derived", "source_data_type": "derived", "source_file": "summary_statistics.csv", "limitation": "Commercial activity proxy; not event attendance, pedestrian counts, or forecast demand."},
    ]


def commercial_rows(spatial: list[dict[str, str]], business: list[dict[str, str]]) -> list[dict[str, Any]]:
    """Aggregate approved spatial and scenario context without exposing raw source rows."""
    rows: list[dict[str, Any]] = []
    for (opportunity, heat), count in sorted(Counter(
        (row["commercial_opportunity"], row["heat_concern"]) for row in spatial
    ).items()):
        rows.append({
            "context_id": f"spatial_{opportunity.lower().replace('/', '_')}_{heat.lower().replace('/', '_')}",
            "context_group": "spatial_heat", "label": f"{opportunity} opportunity / {heat} heat concern",
            "metric_value": count, "unit": "locations", "data_type": "derived",
            "source_data_type": "derived", "source_file": "spatial_heat_locations.csv",
            "limitation": "Exploratory POI/heat context, not verified stadium vendor placement evidence.",
        })
    for placement, count in sorted(Counter(row["placement_class"] for row in business).items()):
        rows.append({
            "context_id": f"business_scenario_{placement.lower()}", "context_group": "business_scenario",
            "label": f"Synthetic business zones: {placement}", "metric_value": count, "unit": "zones",
            "data_type": "derived", "source_data_type": "synthetic",
            "source_file": "finalflow_business_integration.csv",
            "limitation": "Synthetic coordinates, scores, and classifications; not observed placement recommendations.",
        })
    return rows


def weather_heat_rows(weather: list[dict[str, str]], spatial: list[dict[str, str]]) -> list[dict[str, Any]]:
    """Normalize historical weather and derived spatial heat context for one page."""
    rows = [{
        "context_id": row["metric_id"], "label": row["metric_label"],
        "metric_value": float(row["percentage"]), "unit": "percent of station-date observations",
        "threshold": row["threshold"], "recommended_action": row["recommended_action"],
        "data_type": "derived", "source_data_type": row["data_type"],
        "source_file": "weather_risk_summary.csv", "limitation": row["limitation"],
    } for row in weather]
    high_heat = sum(row["heat_concern"] == "High" for row in spatial)
    rows.append({
        "context_id": "spatial_high_heat_locations", "label": "High heat concern locations",
        "metric_value": high_heat, "unit": "exploratory locations", "threshold": "UHI > 7 heuristic",
        "recommended_action": "Review shade and water provision after site validation.",
        "data_type": "derived", "source_data_type": "derived",
        "source_file": "spatial_heat_locations.csv",
        "limitation": "Exploratory spatial context; not venue-specific heat validation.",
    })
    return rows


def recommendation_rows() -> list[dict[str, str]]:
    """Return deterministic display rules, not model-generated recommendations."""
    note = "Curated operational heuristic; requires review and does not establish an optimal or safety-approved action."
    return [
        {"condition_id": "modeled_queue_present", "metric": "queue_passengers", "operator": ">", "threshold": "0", "recommendation": "Keep critical exits clear and review added staging or throughput.", "evidence_type": "derived", "data_type": "derived", "assumption_note": note},
        {"condition_id": "modeled_wait_present", "metric": "estimated_wait_minutes", "operator": ">", "threshold": "0", "recommendation": "Communicate waiting conditions and review wayfinding or staging.", "evidence_type": "derived", "data_type": "derived", "assumption_note": note},
        {"condition_id": "rain_scenario_selected", "metric": "scenario_id", "operator": "==", "threshold": "rain", "recommendation": "Prioritize covered waiting and transfer staging.", "evidence_type": "synthetic", "data_type": "derived", "assumption_note": note},
        {"condition_id": "high_heat_context", "metric": "heat_concern", "operator": "==", "threshold": "High", "recommendation": "Review shade and water provision before outdoor concentration.", "evidence_type": "derived", "data_type": "derived", "assumption_note": note},
        {"condition_id": "synthetic_avoidance_zone", "metric": "placement_class", "operator": "==", "threshold": "Avoided", "recommendation": "Keep vendor activity away from the modeled high-risk zone.", "evidence_type": "synthetic", "data_type": "derived", "assumption_note": note},
    ]


def validate_outputs(outputs: dict[str, list[dict[str, Any]]]) -> None:
    """Check compact dashboard tables before any file is written."""
    config = default_mobility_config()
    scenarios = {scenario.scenario_id.value for scenario in config.scenarios}
    phases = {phase.phase_id.value for phase in config.phases}
    for filename, rows in outputs.items():
        if not rows or list(rows[0]) != OUTPUT_FIELDS[filename]:
            raise ValueError(f"{filename} has an invalid schema")
        keys = set()
        for row in rows:
            if row["data_type"] not in ALLOWED_DATA_TYPES:
                raise ValueError(f"{filename} has invalid data_type")
            if "source_data_type" in row and row["source_data_type"] not in ALLOWED_DATA_TYPES:
                raise ValueError(f"{filename} has invalid source_data_type")
            key = tuple(str(row[column]).strip() for column in PRIMARY_KEYS[filename])
            if not all(key) or key in keys:
                raise ValueError(f"{filename} has missing or duplicate primary keys")
            keys.add(key)
        if filename == "match_timeline_summary.csv":
            if {row["phase_id"] for row in rows} != phases:
                raise ValueError("Timeline phases do not match the mobility contract")
            if [int(row["time_minutes"]) for row in rows] != sorted(int(row["time_minutes"]) for row in rows):
                raise ValueError("Timeline is not ordered")
        if filename == "scenario_comparison.csv" and {row["scenario_id"] for row in rows} != scenarios:
            raise ValueError("Scenario catalog does not match the mobility contract")
        for row in rows:
            for field in ("metric_value", "value", "peak_queue_passengers", "total_clearance_minutes", "passenger_delay_proxy_person_minutes", "overloaded_intervals"):
                if field in row and float(row[field]) < 0:
                    raise ValueError(f"{filename} has a negative metric")


def write_csv(path: Path, rows: list[dict[str, Any]], overwrite: bool) -> None:
    """Write UTF-8 CSV with deterministic order and explicit overwrite protection."""
    if path.exists() and not overwrite:
        raise FileExistsError(f"Refusing to overwrite {path}; use --overwrite")
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=OUTPUT_FIELDS[path.name], lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def run(args: argparse.Namespace) -> dict[str, Any]:
    """Build all app-ready dashboard support exports from reviewed compact inputs."""
    summaries = read_csv(args.mobility_export_dir / "scenario_summary.csv")
    store_summary = read_csv(args.summary_dir / "summary_statistics.csv")[0]
    weather = read_csv(args.summary_dir / "weather_risk_summary.csv")
    spatial = read_csv(args.summary_dir / "spatial_heat_locations.csv")
    business = read_csv(args.business_path)
    scenarios = scenario_rows(summaries)
    outputs = {
        "executive_kpis.csv": executive_rows(store_summary, weather, spatial, scenarios),
        "match_timeline_summary.csv": timeline_rows(),
        "scenario_comparison.csv": scenarios,
        "commercial_context.csv": commercial_rows(spatial, business),
        "weather_heat_context.csv": weather_heat_rows(weather, spatial),
        "recommendation_catalog.csv": recommendation_rows(),
    }
    validate_outputs(outputs)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    for filename, rows in outputs.items():
        write_csv(args.output_dir / filename, rows, args.overwrite)
    context_path = args.output_dir / "finalflow_ai_context.json"
    if context_path.exists() and not args.overwrite:
        raise FileExistsError(f"Refusing to overwrite {context_path}; use --overwrite")
    corridor = read_csv(args.synthetic_dir / "corridor_reference.csv")
    zones = read_csv(args.synthetic_dir / "zone_reference.csv")
    context = {
        "project": "FinalFlow World Cup mobility readiness demonstration",
        "corridor_nodes": corridor,
        "access_zones": zones,
        "scenario_summaries": scenarios,
        "executive_kpis": outputs["executive_kpis.csv"],
        "recommendation_rules": outputs["recommendation_catalog.csv"],
        "provenance": {"data_type": "derived", "source_data_types": ["derived", "synthetic"]},
        "limitations": [
            "Mobility inputs and outputs are synthetic scenario assumptions, not observed operations or forecasts.",
            "Weather context is historical multi-station evidence, not a venue forecast.",
            "Spatial POI/heat data is exploratory context, not verified vendor or access-site evidence.",
            "Synthetic business zone classifications are demonstration examples, not observed recommendations.",
            "Emissions totals are unavailable because documented mode-distance assumptions are missing.",
        ],
    }
    context_path.write_text(json.dumps(context, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    manifest = {
        "schema_version": "1.0.0", "generator_version": GENERATOR_VERSION,
        "config_id": default_mobility_config().config_id,
        "row_counts": {name: len(rows) for name, rows in outputs.items()},
        "provenance": {"data_type": "derived", "source_data_types": ["derived", "synthetic"]},
        "sources": ["data/summaries", "data/synthetic", "data/exports/scenario_summary.csv", str(args.business_path)],
    }
    manifest_path = args.output_dir / "dashboard_context_manifest.json"
    if manifest_path.exists() and not args.overwrite:
        raise FileExistsError(f"Refusing to overwrite {manifest_path}; use --overwrite")
    manifest_path.write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return {"output_dir": str(args.output_dir), "row_counts": manifest["row_counts"], "context": str(context_path)}


def main() -> int:
    """Run the compact dashboard context builder."""
    try:
        result = run(parse_args())
    except (FileExistsError, FileNotFoundError, ValueError, OSError) as error:
        print(f"ERROR: {error}")
        return 1
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
