"""Build compact brand/category monthly summaries for the Streamlit app."""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Any

try:
    import duckdb
except ImportError as error:  # pragma: no cover
    raise SystemExit(
        "DuckDB is required. Install dependencies with: "
        "python -m pip install -r requirements.txt"
    ) from error


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build compact monthly summaries for the Streamlit prototype."
    )
    parser.add_argument(
        "--clean-data",
        type=Path,
        default=Path("data/processed/store_visits_clean.parquet"),
    )
    parser.add_argument(
        "--brand-summary",
        type=Path,
        default=Path("data/summaries/visits_by_brand.csv"),
    )
    parser.add_argument(
        "--category-summary",
        type=Path,
        default=Path("data/summaries/visits_by_category.csv"),
    )
    parser.add_argument(
        "--output-dir", type=Path, default=Path("data/summaries")
    )
    parser.add_argument("--top-brands", type=int, default=50)
    parser.add_argument("--overwrite", action="store_true")
    return parser.parse_args(argv)


def read_labels(path: Path, label: str, limit: int | None = None) -> list[str]:
    if not path.exists():
        raise FileNotFoundError(f"Required summary does not exist: {path}")
    with path.open("r", encoding="utf-8-sig", newline="") as stream:
        rows = list(csv.DictReader(stream))
    required = {label, "total_visits", "data_type"}
    missing = required - set(rows[0] if rows else [])
    if missing:
        raise ValueError(f"{path.name} is missing: {', '.join(sorted(missing))}")
    if any(row["data_type"] != "derived" for row in rows):
        raise ValueError(f"{path.name} must contain only derived rows.")
    rows.sort(key=lambda row: int(row["total_visits"]), reverse=True)
    selected = rows[:limit] if limit else rows
    return [row[label] for row in selected]


def escaped(path: Path) -> str:
    return str(path.resolve()).replace("'", "''")


def build_dimension_summary(
    connection: Any,
    clean_data: Path,
    output: Path,
    dimension: str,
    labels: list[str],
) -> None:
    if dimension not in {"brand", "category"}:
        raise ValueError("dimension must be brand or category")
    connection.execute("CREATE OR REPLACE TEMP TABLE selected_labels(label VARCHAR)")
    connection.executemany(
        "INSERT INTO selected_labels VALUES (?)", [(label,) for label in labels]
    )
    query = f"""
        COPY (
            SELECT
                CAST(date_trunc('month', local_date) AS DATE) AS month,
                {dimension},
                SUM(daily_visits)::BIGINT AS total_visits,
                COUNT(*)::BIGINT AS record_count,
                COUNT(DISTINCT store_id)::BIGINT AS unique_stores,
                ROUND(AVG(daily_visits), 2) AS mean_daily_visits,
                'derived' AS data_type
            FROM read_parquet('{escaped(clean_data)}')
            WHERE {dimension} IN (SELECT label FROM selected_labels)
            GROUP BY 1, 2
            ORDER BY 2, 1
        ) TO '{escaped(output)}' (HEADER, DELIMITER ',')
    """
    connection.execute(query)


def build_brand_category_mix(
    connection: Any,
    clean_data: Path,
    output: Path,
    brands: list[str],
) -> None:
    connection.execute("CREATE OR REPLACE TEMP TABLE selected_labels(label VARCHAR)")
    connection.executemany(
        "INSERT INTO selected_labels VALUES (?)", [(brand,) for brand in brands]
    )
    query = f"""
        COPY (
            SELECT
                brand,
                category,
                COUNT(*)::BIGINT AS record_count,
                SUM(daily_visits)::BIGINT AS total_visits,
                ROUND(AVG(daily_visits), 2) AS mean_daily_visits,
                'derived' AS data_type
            FROM read_parquet('{escaped(clean_data)}')
            WHERE brand IN (SELECT label FROM selected_labels)
            GROUP BY 1, 2
            ORDER BY 1, 3 DESC
        ) TO '{escaped(output)}' (HEADER, DELIMITER ',')
    """
    connection.execute(query)


def run(args: argparse.Namespace) -> dict[str, Any]:
    if args.top_brands < 1:
        raise ValueError("--top-brands must be at least 1.")
    clean_data = args.clean_data.resolve()
    if not clean_data.exists():
        raise FileNotFoundError(f"Clean dataset does not exist: {clean_data}")
    output_dir = args.output_dir.resolve()
    outputs = {
        "brand": output_dir / "brand_monthly_trends.csv",
        "category": output_dir / "category_monthly_trends.csv",
        "brand_category": output_dir / "brand_category_mix.csv",
    }
    existing = [path for path in outputs.values() if path.exists()]
    if existing and not args.overwrite:
        raise FileExistsError(
            "Outputs already exist; pass --overwrite to replace them: "
            + ", ".join(str(path) for path in existing)
        )
    output_dir.mkdir(parents=True, exist_ok=True)
    brands = read_labels(args.brand_summary.resolve(), "brand", args.top_brands)
    categories = read_labels(args.category_summary.resolve(), "category")

    connection = duckdb.connect()
    try:
        connection.execute("SET preserve_insertion_order = false")
        temp_directory = output_dir.parent / "duckdb_tmp" / "streamlit_summaries"
        temp_directory.mkdir(parents=True, exist_ok=True)
        connection.execute("SET threads = 1")
        connection.execute("SET memory_limit = '2GB'")
        connection.execute(
            "SET temp_directory = ?", [str(temp_directory.resolve())]
        )
        build_dimension_summary(
            connection, clean_data, outputs["brand"], "brand", brands
        )
        build_dimension_summary(
            connection, clean_data, outputs["category"], "category", categories
        )
        build_brand_category_mix(
            connection, clean_data, outputs["brand_category"], brands
        )
    finally:
        connection.close()
    return {
        "outputs": {key: str(path) for key, path in outputs.items()},
        "brand_count": len(brands),
        "category_count": len(categories),
        "data_type": "derived",
    }


def main(argv: list[str] | None = None) -> int:
    try:
        result = run(parse_args(argv))
    except (duckdb.Error, OSError, ValueError) as error:
        print(f"Error: {error}", flush=True)
        return 1
    print(json.dumps(result, indent=2), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
