"""Validated loading for the compact data used by the Streamlit prototype."""

from __future__ import annotations

import csv
import math
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]


@dataclass(frozen=True)
class DashboardData:
    summary: dict[str, Any]
    percentiles: dict[str, Any]
    brands: list[dict[str, Any]]
    categories: list[dict[str, Any]]
    markets: list[dict[str, Any]]
    weekdays: list[dict[str, Any]]
    monthly: list[dict[str, Any]]
    brand_monthly: list[dict[str, Any]]
    category_monthly: list[dict[str, Any]]
    scenarios: list[dict[str, Any]]
    weather: list[dict[str, Any]]


SCHEMAS = {
    "summary_statistics.csv": {
        "required": {
            "total_rows",
            "unique_stores",
            "unique_brands",
            "unique_categories",
            "unique_markets",
            "unique_dates",
            "earliest_date",
            "latest_date",
            "total_visits",
            "mean_daily_visits",
            "median_daily_visits",
            "zero_visit_rows",
            "data_type",
        },
        "ints": {
            "total_rows",
            "unique_stores",
            "unique_brands",
            "unique_categories",
            "unique_markets",
            "unique_dates",
            "total_visits",
            "median_daily_visits",
            "zero_visit_rows",
        },
        "floats": {"mean_daily_visits"},
    },
    "visit_percentiles.csv": {
        "required": {"p25", "p50", "p75", "p95", "p99", "p999", "data_type"},
        "ints": {"p25", "p50", "p75", "p95", "p99", "p999"},
        "floats": set(),
    },
    "visits_by_brand.csv": {
        "required": {
            "brand",
            "total_visits",
            "record_count",
            "unique_stores",
            "mean_daily_visits",
            "data_type",
        },
        "ints": {"total_visits", "record_count", "unique_stores"},
        "floats": {"mean_daily_visits"},
    },
    "visits_by_category.csv": {
        "required": {
            "category",
            "total_visits",
            "record_count",
            "unique_stores",
            "mean_daily_visits",
            "data_type",
        },
        "ints": {"total_visits", "record_count", "unique_stores"},
        "floats": {"mean_daily_visits"},
    },
    "visits_by_market.csv": {
        "required": {
            "market",
            "total_visits",
            "record_count",
            "unique_stores",
            "mean_daily_visits",
            "data_type",
        },
        "ints": {"total_visits", "record_count", "unique_stores"},
        "floats": {"mean_daily_visits"},
    },
    "weekday_patterns.csv": {
        "required": {
            "weekday_number",
            "weekday",
            "is_weekend",
            "total_visits",
            "record_count",
            "unique_stores",
            "mean_daily_visits",
            "data_type",
        },
        "ints": {
            "weekday_number",
            "total_visits",
            "record_count",
            "unique_stores",
        },
        "floats": {"mean_daily_visits"},
    },
    "monthly_trends.csv": {
        "required": {
            "month",
            "total_visits",
            "record_count",
            "unique_stores",
            "mean_daily_visits",
            "data_type",
        },
        "ints": {"total_visits", "record_count", "unique_stores"},
        "floats": {"mean_daily_visits"},
    },
    "brand_monthly_trends.csv": {
        "required": {
            "month",
            "brand",
            "total_visits",
            "record_count",
            "unique_stores",
            "mean_daily_visits",
            "data_type",
        },
        "ints": {"total_visits", "record_count", "unique_stores"},
        "floats": {"mean_daily_visits"},
    },
    "category_monthly_trends.csv": {
        "required": {
            "month",
            "category",
            "total_visits",
            "record_count",
            "unique_stores",
            "mean_daily_visits",
            "data_type",
        },
        "ints": {"total_visits", "record_count", "unique_stores"},
        "floats": {"mean_daily_visits"},
    },
    "store_visit_scenarios.csv": {
        "required": {
            "scenario_id",
            "timestamp",
            "match_phase",
            "zone_type",
            "brand",
            "category",
            "baseline_visits",
            "estimated_visits",
            "weather_condition",
            "demand_level",
            "pedestrian_pressure",
            "mobility_conflict_risk",
            "is_synthetic",
            "data_type",
        },
        "ints": {"baseline_visits", "estimated_visits"},
        "floats": set(),
    },
    "weather_risk_summary.csv": {
        "required": {
            "metric_id",
            "metric_label",
            "scope_id",
            "scope_name",
            "period_start",
            "period_end",
            "month_window",
            "observation_unit",
            "numerator",
            "denominator",
            "percentage",
            "threshold",
            "recommended_action",
            "risk_rule_version",
            "data_type",
            "source_file",
            "generated_at",
            "limitation",
        },
        "ints": {"numerator", "denominator"},
        "floats": {"percentage"},
        "allow_extra": False,
    },
    "spatial_heat_locations.csv": {
        "required": {
            "placekey",
            "location_name",
            "market",
            "city",
            "region",
            "latitude",
            "longitude",
            "top_category",
            "includes_parking",
            "spending_level",
            "customer_activity_level",
            "nearby_uhi",
            "uhi_match_method",
            "uhi_match_distance_m",
            "evidence_status",
            "commercial_opportunity",
            "heat_concern",
            "recommendation",
            "reason",
            "is_synthetic",
            "data_type",
            "source_file",
            "generated_at",
        },
        "ints": set(),
        "floats": {"latitude", "longitude"},
        "optional_floats": {"nearby_uhi", "uhi_match_distance_m"},
        "optional_bools": {"includes_parking"},
        "allow_extra": False,
    },
}


def _finite_float(value: str, *, field: str, source: str) -> float:
    try:
        converted = float(value)
    except ValueError as error:
        raise ValueError(f"{source}.{field} must be a number.") from error
    if not math.isfinite(converted):
        raise ValueError(f"{source}.{field} must be finite.")
    return converted


def _strict_bool(
    value: str,
    *,
    field: str,
    source: str,
    allow_empty: bool = False,
) -> bool | None:
    normalized = value.strip().casefold()
    if allow_empty and not normalized:
        return None
    if normalized == "true":
        return True
    if normalized == "false":
        return False
    raise ValueError(f"{source}.{field} must be true or false.")


def read_validated_csv(path: Path) -> list[dict[str, Any]]:
    schema = SCHEMAS[path.name]
    if not path.exists():
        raise FileNotFoundError(
            f"Prepared dashboard data is missing: {path}. "
            "Run the documented data-preparation scripts first."
        )
    with path.open("r", encoding="utf-8-sig", newline="") as stream:
        reader = csv.DictReader(stream)
        columns = set(reader.fieldnames or [])
        missing = schema["required"] - columns
        if missing:
            raise ValueError(
                f"{path.name} is missing columns: {', '.join(sorted(missing))}"
            )
        if not schema.get("allow_extra", True):
            unexpected = columns - schema["required"]
            if unexpected:
                raise ValueError(
                    f"{path.name} has unapproved columns: "
                    f"{', '.join(sorted(unexpected))}"
                )
        rows = list(reader)
    if not rows:
        raise ValueError(f"Prepared dashboard data has no rows: {path}")

    converted: list[dict[str, Any]] = []
    for row in rows:
        normalized = dict(row)
        for field in schema["ints"]:
            normalized[field] = int(normalized[field])
        for field in schema["floats"]:
            normalized[field] = _finite_float(
                normalized[field], field=field, source=path.name
            )
        for field in schema.get("optional_floats", set()):
            normalized[field] = (
                _finite_float(normalized[field], field=field, source=path.name)
                if normalized[field].strip()
                else None
            )
        for field in schema.get("optional_bools", set()):
            normalized[field] = _strict_bool(
                normalized[field],
                field=field,
                source=path.name,
                allow_empty=True,
            )
        if "is_weekend" in normalized:
            normalized["is_weekend"] = _strict_bool(
                normalized["is_weekend"],
                field="is_weekend",
                source=path.name,
            )
        if "is_synthetic" in normalized:
            normalized["is_synthetic"] = _strict_bool(
                normalized["is_synthetic"],
                field="is_synthetic",
                source=path.name,
            )
        converted.append(normalized)
    return converted


def validate_data_types(rows: list[dict[str, Any]], expected: str, source: str) -> None:
    labels = {row.get("data_type") for row in rows}
    if labels != {expected}:
        raise ValueError(
            f"{source} must contain only data_type={expected!r}; found {sorted(labels)}"
        )


def validate_weather_rows(rows: list[dict[str, Any]]) -> None:
    expected_ids = {
        "summer_hot_observation_share",
        "summer_rainy_observation_share",
        "summer_heavy_rain_observation_share",
        "summer_windy_observation_share",
        "summer_low_visibility_observation_share",
        "all_period_low_risk_observation_share",
        "all_period_medium_risk_observation_share",
        "all_period_high_risk_observation_share",
    }
    metric_ids = [row["metric_id"] for row in rows]
    if set(metric_ids) != expected_ids or len(metric_ids) != len(expected_ids):
        raise ValueError("Weather summary must contain each approved metric exactly once.")
    for row in rows:
        if row["observation_unit"] != "station_date_observation":
            raise ValueError("Weather metrics must use station_date_observation units.")
        if row["denominator"] <= 0 or not 0 <= row["numerator"] <= row["denominator"]:
            raise ValueError("Weather numerator and denominator are inconsistent.")
        expected_percentage = round(row["numerator"] / row["denominator"] * 100, 2)
        if abs(row["percentage"] - expected_percentage) > 1e-9:
            raise ValueError("Weather percentage does not match its numerator and denominator.")
        if row["risk_rule_version"] != "weather_risk_rules_v1":
            raise ValueError("Weather risk rule version is not approved.")


@lru_cache(maxsize=2)
def load_dashboard_data(repository_root: str | None = None) -> DashboardData:
    root = Path(repository_root).resolve() if repository_root else REPOSITORY_ROOT
    summaries = root / "data" / "summaries"
    synthetic = root / "data" / "synthetic"

    loaded = {
        name: read_validated_csv(summaries / name)
        for name in (
            "summary_statistics.csv",
            "visit_percentiles.csv",
            "visits_by_brand.csv",
            "visits_by_category.csv",
            "visits_by_market.csv",
            "weekday_patterns.csv",
            "monthly_trends.csv",
            "brand_monthly_trends.csv",
            "category_monthly_trends.csv",
        )
    }
    scenario_rows = read_validated_csv(synthetic / "store_visit_scenarios.csv")
    weather_rows = read_validated_csv(summaries / "weather_risk_summary.csv")
    for name, rows in loaded.items():
        validate_data_types(rows, "derived", name)
    validate_data_types(scenario_rows, "synthetic", "store_visit_scenarios.csv")
    validate_data_types(weather_rows, "derived", "weather_risk_summary.csv")
    validate_weather_rows(weather_rows)
    if not all(row["is_synthetic"] for row in scenario_rows):
        raise ValueError("All scenario records must set is_synthetic=true.")

    return DashboardData(
        summary=loaded["summary_statistics.csv"][0],
        percentiles=loaded["visit_percentiles.csv"][0],
        brands=loaded["visits_by_brand.csv"],
        categories=loaded["visits_by_category.csv"],
        markets=loaded["visits_by_market.csv"],
        weekdays=loaded["weekday_patterns.csv"],
        monthly=loaded["monthly_trends.csv"],
        brand_monthly=loaded["brand_monthly_trends.csv"],
        category_monthly=loaded["category_monthly_trends.csv"],
        scenarios=scenario_rows,
        weather=weather_rows,
    )


@lru_cache(maxsize=2)
def load_spatial_heat_data(
    repository_root: str | None = None,
) -> list[dict[str, Any]]:
    """Load the separately cached spatial table used only by the map page."""
    root = Path(repository_root).resolve() if repository_root else REPOSITORY_ROOT
    rows = read_validated_csv(root / "data" / "summaries" / "spatial_heat_locations.csv")
    validate_data_types(rows, "derived", "spatial_heat_locations.csv")
    if not all(row["is_synthetic"] is False for row in rows):
        raise ValueError("Spatial runtime rows must all set is_synthetic=false.")
    if len({row["placekey"] for row in rows}) != len(rows):
        raise ValueError("Spatial runtime rows must have unique PLACEKEY values.")
    tier_values = {"Low", "Medium", "High"}
    for row in rows:
        if not 40.4 <= row["latitude"] <= 41.1:
            raise ValueError("Spatial latitude falls outside the approved bounds.")
        if not -74.5 <= row["longitude"] <= -73.5:
            raise ValueError("Spatial longitude falls outside the approved bounds.")
        if row["spending_level"] not in tier_values:
            raise ValueError("Spatial spending tier is invalid.")
        if row["customer_activity_level"] not in tier_values:
            raise ValueError("Spatial customer-activity tier is invalid.")
        if row["commercial_opportunity"] != row["spending_level"]:
            raise ValueError("Commercial opportunity must match the approved spending tier.")
        if row["uhi_match_method"] != "nearest_haversine_wgs84_within_limit":
            raise ValueError("Spatial UHI matching method is not approved.")
        if row["nearby_uhi"] is None:
            if row["uhi_match_distance_m"] is not None:
                raise ValueError("Missing UHI cannot have a match distance.")
            if row["evidence_status"] != "missing_uhi":
                raise ValueError("Missing UHI must retain missing_uhi evidence status.")
            if row["heat_concern"] != "Insufficient evidence":
                raise ValueError("Missing UHI must be labeled Insufficient evidence.")
            if row["recommendation"] != "Insufficient evidence":
                raise ValueError("Missing UHI cannot carry an operational recommendation.")
        else:
            if row["uhi_match_distance_m"] is None:
                raise ValueError("Matched UHI must include a distance.")
            if not 0 <= row["uhi_match_distance_m"] <= 250:
                raise ValueError("Spatial UHI match distance exceeds the approved limit.")
            expected_concern = "High" if row["nearby_uhi"] > 7 else "Low/Moderate"
            if row["heat_concern"] != expected_concern:
                raise ValueError("Spatial heat concern does not match its UHI evidence.")
    return rows
