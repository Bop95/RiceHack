"""Validated loading for the compact data used by the Streamlit prototype."""

from __future__ import annotations

import csv
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
}


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
        rows = list(reader)
    if not rows:
        raise ValueError(f"Prepared dashboard data has no rows: {path}")

    converted: list[dict[str, Any]] = []
    for row in rows:
        normalized = dict(row)
        for field in schema["ints"]:
            normalized[field] = int(normalized[field])
        for field in schema["floats"]:
            normalized[field] = float(normalized[field])
        if "is_weekend" in normalized:
            normalized["is_weekend"] = normalized["is_weekend"].lower() == "true"
        if "is_synthetic" in normalized:
            normalized["is_synthetic"] = (
                normalized["is_synthetic"].lower() == "true"
            )
        converted.append(normalized)
    return converted


def validate_data_types(rows: list[dict[str, Any]], expected: str, source: str) -> None:
    labels = {row.get("data_type") for row in rows}
    if labels != {expected}:
        raise ValueError(
            f"{source} must contain only data_type={expected!r}; found {sorted(labels)}"
        )


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
    for name, rows in loaded.items():
        validate_data_types(rows, "derived", name)
    validate_data_types(scenario_rows, "synthetic", "store_visit_scenarios.csv")
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
    )
