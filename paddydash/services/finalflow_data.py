"""Safe, cached readers for compact FinalFlow exports and synthetic references."""

from __future__ import annotations

import csv
import json
import math
from datetime import datetime
from pathlib import Path
from typing import Any

import streamlit as st

from paddydash.services.mobility_config import default_mobility_config


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
EXPORTS_DIR = REPOSITORY_ROOT / "data" / "exports"
SYNTHETIC_DIR = REPOSITORY_ROOT / "data" / "synthetic"


def repository_file(category: str, filename: str) -> Path:
    """Resolve a known data category without accepting machine-specific paths."""
    directories = {"exports": EXPORTS_DIR, "synthetic": SYNTHETIC_DIR,
                   "weather": REPOSITORY_ROOT / "notebooks/tan-dat/data/summaries"}
    if category not in directories or Path(filename).name != filename:
        raise ValueError("Unsupported FinalFlow data path")
    return directories[category] / filename


@st.cache_data(show_spinner=False, ttl=60)
def load_csv_safe(category: str, filename: str) -> tuple[list[dict[str, str]], str | None]:
    """Return compact CSV rows or a concise unavailable message."""
    path = repository_file(category, filename)
    if not path.is_file():
        return [], f"{filename} is unavailable."
    try:
        with path.open(newline="", encoding="utf-8") as stream:
            reader = csv.DictReader(stream)
            if reader.fieldnames is None:
                return [], f"{filename} has no header."
            return list(reader), None
    except (OSError, UnicodeDecodeError, csv.Error):
        return [], f"{filename} could not be read."


@st.cache_data(show_spinner=False, ttl=60)
def load_json_safe(category: str, filename: str) -> tuple[dict[str, Any] | None, str | None]:
    """Return compact JSON content or a concise unavailable message."""
    path = repository_file(category, filename)
    if not path.is_file():
        return None, f"{filename} is unavailable."
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        return None, f"{filename} could not be read."
    if not isinstance(payload, dict):
        return None, f"{filename} has an invalid JSON object."
    return payload, None


def find_row(rows: list[dict[str, str]], field: str, value: str) -> dict[str, str] | None:
    """Find one compact record without raising if a table is incomplete."""
    return next((row for row in rows if row.get(field) == value), None)


# Primary keys and numeric fields of the prepared public dashboard tables.
TABLES = {
    "mobility_node_timeseries.csv": ("scenario_id time_minutes node_id", "incoming_passengers queue_passengers holding_passengers served_passengers departing_passengers utilization estimated_wait_minutes", "timestamp phase_id assumption_note"),
    "mobility_edge_timeseries.csv": ("scenario_id time_minutes edge_id", "demand capacity throughput utilization in_transit_passengers", "timestamp phase_id assumption_note"),
    "scenario_summary.csv": ("scenario_id", "peak_queue_passengers peak_post_final_whistle_queue_passengers peak_utilization total_clearance_minutes passenger_delay_proxy_person_minutes overloaded_intervals total_arrivals total_departures direct_access_arrivals peak_queue_improvement_vs_baseline delay_proxy_improvement_vs_baseline", "bottleneck_node assumption_note"),
    "scenario_comparison.csv": ("scenario_id", "peak_queue_passengers peak_post_final_whistle_queue_passengers total_clearance_minutes passenger_delay_proxy_person_minutes overloaded_intervals", "name description primary_change source_data_type"),
    "mobility_access_summary.csv": ("scenario_id", "peak_pedestrian_load_ratio peak_parking_utilization peak_rideshare_passengers peak_shuttle_passengers rail_passenger_total walk_passenger_total road_passenger_total shuttle_passenger_total", "shuttle_utilization_status assumption_note"),
    "match_timeline_summary.csv": ("phase_id", "time_minutes", "display_name start_time direction expected_pressure_level source_data_type"),
    "executive_kpis.csv": ("kpi_id", "value", "label unit source_data_type source_file limitation"),
    "commercial_context.csv": ("context_id", "metric_value", "context_group label unit source_data_type source_file limitation"),
    "weather_heat_context.csv": ("context_id", "metric_value", "label unit threshold recommended_action source_data_type source_file limitation"),
    "recommendation_catalog.csv": ("condition_id", "", "metric operator threshold recommendation evidence_type assumption_note"),
    "intervention_comparison.csv": ("intervention_id", "baseline_peak_queue_passengers scenario_peak_queue_passengers peak_queue_improvement baseline_delay_proxy_person_minutes scenario_delay_proxy_person_minutes delay_proxy_improvement", "name target_id comparison_scenario_id evaluation_status assumption_note"),
    "corridor_reference.csv": ("node_id", "order latitude longitude", "display_name node_type confidence_type assumption_note"),
    "transit_service_capacity.csv": ("scenario_id time_minutes edge_id", "scheduled_capacity effective_capacity service_frequency_minutes disruption_factor weather_factor", "timestamp phase_id from_node to_node mode confidence_type assumption_note"),
    "weather_monthly.csv": ("month", "month temp_max_avg temp_avg_mean temp_min_avg humidity_avg wind_speed_avg total_precip_mm rainy_days", ""),
}


def validate_rows(filename: str, rows: list[dict]) -> list[dict[str, Any]]:
    """Type and validate a table without changing its source rows."""
    if not rows:
        raise ValueError(f"{filename} contains no records.")
    keys, numbers, extra = (part.split() for part in TABLES[filename])
    config = default_mobility_config()
    nodes = {n.node_id for n in config.nodes}
    edges = {e.edge_id for e in config.edges}
    phases = {p.phase_id.value for p in config.phases}
    scenarios = {s.scenario_id.value for s in config.scenarios}
    expected_type = "synthetic" if filename in {"corridor_reference.csv", "transit_service_capacity.csv"} else "derived"
    required = set(keys + numbers + extra)
    if filename != "weather_monthly.csv":
        required.add("data_type")
    seen = set()
    clock_origin = None
    typed = []
    for raw in rows:
        if not required.issubset(raw) or None in raw or any(raw[k] in (None, "") for k in keys):
            raise ValueError(f"{filename} has missing fields or identifiers.")
        row = dict(raw)
        for field in set(numbers) | ({"time_minutes"} if "time_minutes" in row else set()):
            value = row[field]
            nullable = field in {"utilization", "estimated_wait_minutes", "total_clearance_minutes"} or (
                filename == "intervention_comparison.csv" and row["evaluation_status"] == "catalog_only_not_modeled")
            if value in ("", None) and nullable:
                row[field] = None
                continue
            number = float(value)
            if not math.isfinite(number):
                raise ValueError(f"{filename} contains a non-finite number.")
            signed = field in {"time_minutes", "latitude", "longitude", "temp_max_avg", "temp_avg_mean", "temp_min_avg"} or "improvement" in field
            if number < 0 and not signed:
                raise ValueError(f"{filename} contains a negative count or capacity.")
            if (field.endswith('_passengers') or field in {'queue_passengers', 'demand', 'capacity', 'throughput', 'order', 'month', 'overloaded_intervals', 'total_arrivals', 'total_departures'}) and not number.is_integer():
                raise ValueError(f"{filename} contains a fractional passenger count or capacity.")
            row[field] = int(number) if number.is_integer() else number
        identity = tuple(row[k] for k in keys)
        if identity in seen:
            raise ValueError(f"{filename} contains duplicate primary keys.")
        seen.add(identity)
        for field, allowed in (("scenario_id", scenarios), ("phase_id", phases), ("node_id", nodes),
                               ("edge_id", edges), ("from_node", nodes), ("to_node", nodes), ("bottleneck_node", nodes)):
            if field in row and row[field] not in allowed:
                raise ValueError(f"{filename} contains an unknown {field}.")
        if filename == "weather_monthly.csv":
            row["month"] = int(row["month"])
            if not 1 <= row["month"] <= 12 or not 0 <= row["humidity_avg"] <= 100 or not -90 <= row["temp_min_avg"] <= row["temp_avg_mean"] <= row["temp_max_avg"] <= 60:
                raise ValueError("Monthly weather values are invalid.")
            row.update(data_type="derived", source_file="weather_monthly.csv")
        elif row["data_type"] != expected_type:
            raise ValueError(f"{filename} has unexpected provenance.")
        for field in ("source_data_type", "evidence_type"):
            if field in row and row[field] not in {"provided", "derived", "synthetic", "web"}:
                raise ValueError(f"{filename} has invalid evidence provenance.")
        if "time_minutes" in row and row["time_minutes"] % config.time_step_minutes:
            raise ValueError(f"{filename} has misaligned intervals.")
        if "timestamp" in row:
            stamp = datetime.fromisoformat(row["timestamp"].replace("Z", "+00:00"))
            if stamp.utcoffset() is None or stamp.second or stamp.microsecond or stamp.minute % config.time_step_minutes:
                raise ValueError(f"{filename} has invalid timestamps.")
            origin = stamp.timestamp() - row['time_minutes'] * 60
            if clock_origin is not None and origin != clock_origin:
                raise ValueError(f"{filename} has inconsistent replay timestamps.")
            clock_origin = origin
        if "throughput" in row and row["throughput"] > min(row["demand"], row["capacity"]):
            raise ValueError("Edge throughput exceeds demand or capacity.")
        if "latitude" in row and (not -90 <= row["latitude"] <= 90 or not -180 <= row["longitude"] <= 180):
            raise ValueError("Coordinates are outside valid bounds.")
        if filename == "intervention_comparison.csv":
            if row["evaluation_status"] not in {"modeled", "catalog_only_not_modeled"}:
                raise ValueError("Unknown intervention evaluation status.")
            if row["evaluation_status"] == "modeled" and row["comparison_scenario_id"] not in scenarios:
                raise ValueError("Unknown intervention scenario.")
        typed.append(row)
    return typed


@st.cache_data(show_spinner=False, ttl=60)
def load_table(filename: str) -> tuple[list[dict[str, Any]], str | None]:
    """Load one independently validated prepared table, returning safe errors."""
    if filename == 'weather_risk_summary.csv':
        from paddydash.services.data_service import read_validated_csv, validate_weather_rows, validate_data_types
        try:
            rows = read_validated_csv(REPOSITORY_ROOT / 'data/summaries' / filename)
            validate_weather_rows(rows)
            validate_data_types(rows, 'derived', filename)
            return rows, None
        except (OSError, ValueError, TypeError, KeyError):
            return [], 'Reviewed weather risk summary is unavailable.'
    category = "synthetic" if filename in {"corridor_reference.csv", "transit_service_capacity.csv"} else "weather" if filename == "weather_monthly.csv" else "exports"
    rows, error = load_csv_safe(category, filename)
    if error:
        return [], error
    try:
        return validate_rows(filename, rows), None
    except (ValueError, KeyError, TypeError, OverflowError):
        return [], f"{filename} is unavailable because its schema or values are invalid."


def phase_window(phase_id: str) -> tuple[int, int, int]:
    """Return selectable bounds and the default minute; coincident events share a boundary."""
    config = default_mobility_config()
    phase = next(p for p in config.phases if p.phase_id.value == phase_id)
    start = phase.start_minute
    end = start
    if phase.kind == "interval":
        following = [p.start_minute for p in config.phases if p.start_minute > start]
        rows, _ = load_table("mobility_node_timeseries.csv")
        end = min(following) - config.time_step_minutes if following else max((r["time_minutes"] for r in rows), default=start)
    preview = min(end, -135) if phase_id == "pre_match" else min(end, start + 30) if phase_id == "post_match" else start
    return start, end, max(start, preview)


def percent_change(baseline: float | None, selected: float | None) -> float | None:
    """Return signed percentage change; zero/missing baselines have no percentage."""
    return None if baseline in (None, 0) or selected is None else (selected - baseline) / baseline * 100


def change_text(label: str, baseline: float | None, selected: float | None) -> str:
    if baseline is None or selected is None:
        return f"{label}: comparison unavailable."
    if baseline == selected:
        return f"{label} is unchanged at {selected:,.0f}."
    delta = selected - baseline
    percent = percent_change(baseline, selected)
    suffix = f" ({percent:+.1f}%)" if percent is not None else " (percentage unavailable: zero baseline)"
    return f"{label}: {baseline:,.0f} to {selected:,.0f}, change {delta:+,.0f}{suffix}."


def evaluate_rules(rules: list[dict], evidence: dict[str, dict]) -> list[dict]:
    """Evaluate only supported catalog rules against explicitly scoped evidence."""
    results = []
    for rule in rules:
        item = evidence.get(rule["metric"])
        if not item or item.get("value") is None:
            continue
        value, threshold = item["value"], rule["threshold"]
        try:
            matches = (str(value) == str(threshold) if rule["operator"] == "==" else
                       float(value) > float(threshold) if rule["operator"] == ">" else False)
        except (TypeError, ValueError):
            matches = False
        if matches:
            results.append({**rule, "trigger_value": value, "source_file": item["source_file"],
                            "scope": item["scope"]})
    return results


def current_mobility(scenario_id: str, minute: int) -> dict[str, Any]:
    """Calculate current metrics only from complete exported node/edge snapshots."""
    nodes, node_error = load_table("mobility_node_timeseries.csv")
    edges, edge_error = load_table("mobility_edge_timeseries.csv")
    summaries, summary_error = load_table("scenario_summary.csv")
    selected_nodes = [r for r in nodes if r["scenario_id"] == scenario_id and r["time_minutes"] == minute]
    selected_edges = [r for r in edges if r["scenario_id"] == scenario_id and r["time_minutes"] == minute]
    config = default_mobility_config()
    order = {n.node_id: n.order for n in config.nodes}
    selected_nodes.sort(key=lambda r: order[r["node_id"]])
    error = node_error or edge_error
    if len(selected_nodes) != len(config.nodes) or len(selected_edges) != len(config.edges):
        error = error or "Mobility snapshot is incomplete for the selected time."
    if len({r['timestamp'] for r in selected_nodes + selected_edges}) != 1:
        error = error or "Mobility tables do not share the same replay timestamp."
    summary = next((r for r in summaries if r["scenario_id"] == scenario_id), None)
    result = dict(nodes=selected_nodes, edges=selected_edges, summary=summary,
                  summary_error=summary_error, error=error, available=not error, time_minutes=minute,
                  scenario_id=scenario_id, data_type="derived", queue=None, pressure=None,
                  utilization=None, wait=None, bottleneck="Unavailable", status="Unavailable")
    if error:
        return result
    biggest = max(selected_nodes, key=lambda r: r["queue_passengers"])
    waits = [r["estimated_wait_minutes"] for r in selected_nodes]
    pressure = sum(r["queue_passengers"] for r in selected_nodes)
    utilization = max((r["utilization"] or 0) for r in selected_edges)
    wait = None if None in waits else max(waits)
    holding = sum(r["holding_passengers"] for r in selected_nodes)
    traveling = sum(r["in_transit_passengers"] for r in selected_edges)
    whistle = next(p.start_minute for p in config.phases if p.phase_id.value == "final_whistle")
    status = "Blocked" if wait is None else "Queueing" if pressure else "Holding" if holding else "Flowing" if traveling or utilization else "Cleared" if minute > whistle else "Not started"
    names = {n.node_id: n.name for n in config.nodes}
    result.update(queue=biggest["queue_passengers"], pressure=pressure, utilization=utilization,
                  wait=wait, bottleneck=names[biggest["node_id"]] if pressure else "None",
                  bottleneck_id=biggest["node_id"] if pressure else None, status=status)
    return result
