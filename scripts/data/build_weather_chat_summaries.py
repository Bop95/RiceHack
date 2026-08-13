"""Build the compact historical weather summary used by Ask FinalFlow."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
from collections import Counter
from datetime import date
from pathlib import Path
from typing import Any


RISK_RULE_VERSION = "weather_risk_rules_v1"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("data/summaries/weather_risk_summary.csv"),
    )
    parser.add_argument(
        "--metadata",
        type=Path,
        default=None,
        help="Defaults to <output stem>.metadata.json beside --output.",
    )
    parser.add_argument("--generated-at", required=True)
    parser.add_argument("--source-commit", default="43160ef")
    args = parser.parse_args()
    if args.metadata is None:
        args.metadata = args.output.with_suffix(".metadata.json")
    return args


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    """Write deployment CSVs with deterministic bytes on every platform."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(
            stream,
            fieldnames=list(rows[0]),
            lineterminator="\n",
        )
        writer.writeheader()
        writer.writerows(rows)


def parse_float(row: dict[str, str], field: str) -> float:
    result = float(row[field])
    if not math.isfinite(result):
        raise ValueError(f"{field} must be finite")
    return result


def risk_flags(row: dict[str, str]) -> tuple[bool, bool, bool, bool]:
    return (
        parse_float(row, "temperature_max_c") >= 30.0,
        parse_float(row, "precipitation_mm") > 0.0,
        parse_float(row, "wind_speed_knots") >= 20.0,
        parse_float(row, "visibility_km") <= 5.0,
    )


def risk_level(flags: tuple[bool, bool, bool, bool]) -> str:
    hot, rainy, windy, low_visibility = flags
    score = 0.35 * hot + 0.30 * rainy + 0.15 * windy + 0.20 * low_visibility
    if score >= 0.6:
        return "High"
    if score >= 0.3:
        return "Medium"
    return "Low"


def metric_row(
    *,
    metric_id: str,
    label: str,
    numerator: int,
    denominator: int,
    threshold: str,
    action: str,
    period_start: str,
    period_end: str,
    month_window: str,
    generated_at: str,
    limitation: str,
) -> dict[str, Any]:
    return {
        "metric_id": metric_id,
        "metric_label": label,
        "scope_id": "reviewed_multi_station_dataset",
        "scope_name": "Reviewed multi-station weather dataset",
        "period_start": period_start,
        "period_end": period_end,
        "month_window": month_window,
        "observation_unit": "station_date_observation",
        "numerator": numerator,
        "denominator": denominator,
        "percentage": round(numerator / denominator * 100, 2),
        "threshold": threshold,
        "recommended_action": action,
        "risk_rule_version": RISK_RULE_VERSION,
        "data_type": "derived",
        "source_file": "daily_weather_clean.csv",
        "generated_at": generated_at,
        "limitation": limitation,
    }


def build(args: argparse.Namespace) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    all_count = 0
    input_count = 0
    summer_count = 0
    dates: set[date] = set()
    stations: set[str] = set()
    earliest: date | None = None
    latest: date | None = None
    summer_flags: Counter[str] = Counter()
    levels: Counter[str] = Counter()
    rejected: Counter[str] = Counter()
    seen_observations: set[tuple[str, date]] = set()
    with args.input.open("r", encoding="utf-8-sig", newline="") as stream:
        reader = csv.DictReader(stream)
        required = {
            "location_id",
            "date",
            "temperature_min_c",
            "temperature_avg_c",
            "temperature_max_c",
            "precipitation_raw",
            "precipitation_mm",
            "wind_speed_knots",
            "visibility_km",
        }
        missing = required - set(reader.fieldnames or [])
        if missing:
            raise ValueError(f"Weather input is missing: {', '.join(sorted(missing))}")
        for row in reader:
            input_count += 1
            station = row["location_id"].strip()
            try:
                observation_date = date.fromisoformat(row["date"])
                minimum = parse_float(row, "temperature_min_c")
                average = parse_float(row, "temperature_avg_c")
                maximum = parse_float(row, "temperature_max_c")
                precipitation_raw = parse_float(row, "precipitation_raw")
                precipitation_mm = parse_float(row, "precipitation_mm")
                parse_float(row, "wind_speed_knots")
                parse_float(row, "visibility_km")
            except (KeyError, TypeError, ValueError):
                rejected["invalid_observation"] += 1
                continue
            if not station:
                rejected["missing_station"] += 1
                continue
            observation_key = (station, observation_date)
            if not minimum <= average <= maximum:
                rejected["invalid_temperature_order"] += 1
                continue
            expected_precipitation = (
                0.0 if precipitation_raw < 0 else precipitation_raw / 100.0
            )
            if abs(precipitation_mm - expected_precipitation) > 1e-9:
                rejected["invalid_precipitation_conversion"] += 1
                continue
            if observation_key in seen_observations:
                rejected["duplicate_station_date"] += 1
                continue
            seen_observations.add(observation_key)
            flags = risk_flags(row)
            levels[risk_level(flags)] += 1
            all_count += 1
            dates.add(observation_date)
            stations.add(station)
            earliest = observation_date if earliest is None else min(earliest, observation_date)
            latest = observation_date if latest is None else max(latest, observation_date)
            if observation_date.month in (6, 7):
                summer_count += 1
                hot, rainy, windy, low_visibility = flags
                summer_flags["hot"] += hot
                summer_flags["rainy"] += rainy
                summer_flags["heavy_rain"] += precipitation_mm > 20.0
                summer_flags["windy"] += windy
                summer_flags["low_visibility"] += low_visibility

    if earliest is None or latest is None or not all_count or not summer_count:
        raise ValueError("Weather input contains no eligible observations.")
    period_start = earliest.isoformat()
    period_end = latest.isoformat()
    historical_limitation = (
        "Historical multi-station evidence; not a live forecast or a venue-specific claim."
    )
    rows = [
        metric_row(
            metric_id="summer_hot_observation_share",
            label="Hot June-July observations",
            numerator=summer_flags["hot"],
            denominator=summer_count,
            threshold="maximum temperature >= 30 C",
            action="Add water points and shade",
            period_start=period_start,
            period_end=period_end,
            month_window="June-July",
            generated_at=args.generated_at,
            limitation=historical_limitation,
        ),
        metric_row(
            metric_id="summer_rainy_observation_share",
            label="Rainy June-July observations",
            numerator=summer_flags["rainy"],
            denominator=summer_count,
            threshold="precipitation > 0 mm",
            action="Add covered waiting and shuttle capacity",
            period_start=period_start,
            period_end=period_end,
            month_window="June-July",
            generated_at=args.generated_at,
            limitation=historical_limitation,
        ),
        metric_row(
            metric_id="summer_heavy_rain_observation_share",
            label="Heavy-rain June-July observations",
            numerator=summer_flags["heavy_rain"],
            denominator=summer_count,
            threshold="precipitation > 20 mm",
            action="Stage additional covered capacity and monitor disruption risk",
            period_start=period_start,
            period_end=period_end,
            month_window="June-July",
            generated_at=args.generated_at,
            limitation=historical_limitation,
        ),
        metric_row(
            metric_id="summer_windy_observation_share",
            label="Windy June-July observations",
            numerator=summer_flags["windy"],
            denominator=summer_count,
            threshold="wind speed >= 20 knots",
            action="Secure temporary structures",
            period_start=period_start,
            period_end=period_end,
            month_window="June-July",
            generated_at=args.generated_at,
            limitation=historical_limitation,
        ),
        metric_row(
            metric_id="summer_low_visibility_observation_share",
            label="Low-visibility June-July observations",
            numerator=summer_flags["low_visibility"],
            denominator=summer_count,
            threshold="visibility <= 5 km",
            action="Use slower vehicle assumptions and active staff guidance",
            period_start=period_start,
            period_end=period_end,
            month_window="June-July",
            generated_at=args.generated_at,
            limitation=historical_limitation,
        ),
    ]
    for level in ("Low", "Medium", "High"):
        rows.append(
            metric_row(
                metric_id=f"all_period_{level.casefold()}_risk_observation_share",
                label=f"{level}-risk observations",
                numerator=levels[level],
                denominator=all_count,
                threshold=f"FinalFlow {level.casefold()} risk-score band",
                action={
                    "Low": "Normal operations",
                    "Medium": "Apply the actions triggered by the active weather flags",
                    "High": "Apply all triggered actions and increase operational monitoring",
                }[level],
                period_start=period_start,
                period_end=period_end,
                month_window="All months",
                generated_at=args.generated_at,
                limitation=(
                    historical_limitation
                    + " Risk bands are FinalFlow project heuristics, not scientific standards."
                ),
            )
        )
    metadata = {
        "artifact": args.output.as_posix(),
        "source_branch": "tan-dat-final",
        "source_commit": args.source_commit,
        "source_files": {args.input.name: sha256(args.input)},
        "generated_at": args.generated_at,
        "risk_rule_version": RISK_RULE_VERSION,
        "observation_unit": "station_date_observation",
        "scope": "reviewed multi-station dataset; no venue mapping approved",
        "input_rows": input_count,
        "accepted_observation_rows": all_count,
        "rejected_observation_rows": sum(rejected.values()),
        "rejected_by_reason": dict(rejected),
        "accepted_rows": len(rows),
        "summer_observations": summer_count,
        "unique_dates": len(dates),
        "unique_stations": len(stations),
        "risk_level_counts": dict(levels),
        "limitations": [
            historical_limitation,
            "Risk thresholds, weights, levels, and actions are FinalFlow project heuristics.",
        ],
    }
    return rows, metadata


def main() -> int:
    args = parse_args()
    rows, metadata = build(args)
    write_csv(args.output, rows)
    metadata["artifact_sha256"] = sha256(args.output)
    args.metadata.parent.mkdir(parents=True, exist_ok=True)
    args.metadata.write_text(
        json.dumps(metadata, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print(f"Wrote {len(rows)} weather summary rows to {args.output}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
