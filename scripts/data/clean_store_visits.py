"""Clean and summarize the Rice store-visit dataset with DuckDB.

The pipeline streams CSV or CSV.GZ files through DuckDB so the complete dataset
does not need to fit in memory. It never edits the provided source files.

Outputs
-------
data/processed/store_visits_clean.parquet
data/summaries/data_quality_report.md
data/summaries/summary_statistics.csv
data/summaries/visit_percentiles.csv
data/summaries/visits_by_brand.csv
data/summaries/visits_by_category.csv
data/summaries/visits_by_market.csv
data/summaries/weekday_patterns.csv
data/summaries/monthly_trends.csv
"""

from __future__ import annotations

import argparse
import csv
import glob
import gzip
import json
import re
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, TextIO

try:
    import duckdb
except ImportError as error:  # pragma: no cover - only reached without dependency.
    raise SystemExit(
        "DuckDB is required. Install it with: "
        "python -m pip install 'duckdb>=1.3,<2'"
    ) from error


EXPECTED_COLUMNS = [
    "BRAND",
    "CATEGORY",
    "DAILY_VISITS",
    "LOCAL_DATE",
    "MARKET",
    "NAICS_CODE",
    "NAME",
    "STATE",
    "STOCK_EXCHANGE",
    "STOCK_SYMBOL",
    "STORE_ID",
    "SUB_CATEGORY",
    "VERSION_ID",
]

SUMMARY_FILENAMES = [
    "data_quality_report.md",
    "summary_statistics.csv",
    "visit_percentiles.csv",
    "visits_by_brand.csv",
    "visits_by_category.csv",
    "visits_by_market.csv",
    "weekday_patterns.csv",
    "monthly_trends.csv",
]

MEMORY_PATTERN = re.compile(r"^[1-9][0-9]*(?:MB|GB)$", re.IGNORECASE)
DUPLICATE_BUCKET_COUNT = 64


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Clean and summarize Rice store-visit CSV/CSV.GZ files."
    )
    parser.add_argument(
        "--input",
        required=True,
        help="One CSV/CSV.GZ file, a directory, or a glob pattern.",
    )
    parser.add_argument(
        "--output-root",
        type=Path,
        default=Path("data"),
        help="Output root containing processed/ and summaries/ (default: data).",
    )
    parser.add_argument("--threads", type=int, default=4)
    parser.add_argument(
        "--memory-limit",
        default="8GB",
        help="DuckDB memory limit such as 4GB or 8000MB (default: 8GB).",
    )
    parser.add_argument(
        "--limit",
        type=int,
        help="Optional row limit for testing only. Omit for the complete dataset.",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Replace this pipeline's existing outputs.",
    )
    parser.add_argument(
        "--resume",
        action="store_true",
        help="Reuse a complete candidate Parquet left by an interrupted run.",
    )
    return parser.parse_args(argv)


def discover_input_files(input_value: str) -> list[Path]:
    """Resolve a file, directory, or glob into sorted source files."""
    candidate = Path(input_value).expanduser()
    if candidate.is_file():
        files = [candidate]
    elif candidate.is_dir():
        files = sorted(candidate.glob("*.csv.gz")) + sorted(candidate.glob("*.csv"))
    else:
        files = [Path(match) for match in sorted(glob.glob(input_value))]

    files = [path.resolve() for path in files if path.is_file()]
    if not files:
        raise FileNotFoundError(f"No input files found for: {input_value}")
    unsupported = [path for path in files if not path.name.lower().endswith((".csv", ".csv.gz"))]
    if unsupported:
        raise ValueError(f"Unsupported input file: {unsupported[0]}")
    return files


def open_text_source(path: Path) -> TextIO:
    if path.name.lower().endswith(".gz"):
        return gzip.open(path, "rt", encoding="utf-8-sig", newline="")
    return path.open("r", encoding="utf-8-sig", newline="")


def validate_headers(files: list[Path]) -> None:
    """Require the documented 13-column schema in every source file."""
    for path in files:
        with open_text_source(path) as stream:
            reader = csv.reader(stream)
            try:
                header = next(reader)
            except StopIteration as error:
                raise ValueError(f"Source file is empty: {path}") from error
        if header != EXPECTED_COLUMNS:
            raise ValueError(
                f"Unexpected header in {path.name}.\n"
                f"Expected: {EXPECTED_COLUMNS}\n"
                f"Found:    {header}"
            )


def sql_literal(value: str | Path) -> str:
    return "'" + str(value).replace("'", "''") + "'"


def sql_file_list(files: list[Path]) -> str:
    return "[" + ", ".join(sql_literal(path.as_posix()) for path in files) + "]"


def ensure_safe_options(args: argparse.Namespace) -> None:
    if args.threads < 1:
        raise ValueError("--threads must be at least 1.")
    if not MEMORY_PATTERN.fullmatch(args.memory_limit):
        raise ValueError("--memory-limit must look like 4GB or 8000MB.")
    if args.limit is not None and args.limit < 1:
        raise ValueError("--limit must be at least 1 when supplied.")
    if args.overwrite and args.resume:
        raise ValueError("Use either --overwrite or --resume, not both.")


def expected_output_paths(output_root: Path) -> list[Path]:
    return [
        output_root / "processed" / "store_visits_clean.parquet",
        *[output_root / "summaries" / name for name in SUMMARY_FILENAMES],
    ]


def prepare_workspace(output_root: Path, overwrite: bool, resume: bool) -> Path:
    outputs = expected_output_paths(output_root)
    existing = [path for path in outputs if path.exists()]
    if existing and not overwrite:
        raise FileExistsError(
            f"Output already exists: {existing[0]}. Use --overwrite to replace outputs."
        )

    work_root = output_root / ".store_visits_work"
    if resume:
        candidate = work_root / "processed" / "store_visits_clean_candidate.parquet"
        clean = work_root / "processed" / "store_visits_clean.parquet"
        if not candidate.exists() or clean.exists():
            raise FileNotFoundError(
                "--resume requires an existing clean candidate and no completed work "
                f"Parquet under {work_root / 'processed'}."
            )
        (work_root / "summaries").mkdir(parents=True, exist_ok=True)
        for name in SUMMARY_FILENAMES:
            partial = work_root / "summaries" / name
            if partial.exists():
                partial.unlink()
        (output_root / "duckdb_tmp").mkdir(parents=True, exist_ok=True)
        return work_root

    if work_root.exists():
        if not overwrite:
            raise FileExistsError(
                f"Previous work directory exists: {work_root}. Use --overwrite after review."
            )
        shutil.rmtree(work_root)
    (work_root / "processed").mkdir(parents=True)
    (work_root / "summaries").mkdir(parents=True)
    (output_root / "duckdb_tmp").mkdir(parents=True, exist_ok=True)
    return work_root


def configure_connection(
    connection: duckdb.DuckDBPyConnection,
    output_root: Path,
    threads: int,
    memory_limit: str,
) -> None:
    connection.execute(f"SET threads = {threads}")
    connection.execute(f"SET memory_limit = {sql_literal(memory_limit.upper())}")
    connection.execute("SET preserve_insertion_order = false")
    connection.execute("SET max_temp_directory_size = '20GB'")
    temp_path = (output_root / "duckdb_tmp").resolve().as_posix()
    connection.execute(f"SET temp_directory = {sql_literal(temp_path)}")


def create_source_views(
    connection: duckdb.DuckDBPyConnection,
    files: list[Path],
    limit: int | None,
) -> None:
    source = (
        "SELECT * FROM read_csv("
        f"{sql_file_list(files)}, header = true, all_varchar = true, "
        "union_by_name = false, compression = 'auto')"
    )
    if limit is not None:
        source = f"SELECT * FROM ({source}) LIMIT {limit}"

    connection.execute(f"CREATE TEMP VIEW raw_store_visits AS {source}")
    connection.execute(
        """
        CREATE TEMP VIEW typed_store_visits AS
        SELECT
            NULLIF(TRIM(BRAND), '') AS brand,
            NULLIF(TRIM(CATEGORY), '') AS category,
            CASE
                WHEN REGEXP_FULL_MATCH(NULLIF(TRIM(DAILY_VISITS), ''), '[+-]?[0-9]+')
                THEN TRY_CAST(TRIM(DAILY_VISITS) AS BIGINT)
            END AS daily_visits,
            TRY_STRPTIME(NULLIF(TRIM(LOCAL_DATE), ''), '%Y-%m-%d')::DATE AS local_date,
            NULLIF(TRIM(MARKET), '') AS market,
            NULLIF(TRIM(NAICS_CODE), '') AS naics_code,
            NULLIF(TRIM(NAME), '') AS name,
            UPPER(NULLIF(TRIM(STATE), '')) AS state,
            UPPER(NULLIF(TRIM(STOCK_EXCHANGE), '')) AS stock_exchange,
            UPPER(NULLIF(TRIM(STOCK_SYMBOL), '')) AS stock_symbol,
            NULLIF(TRIM(STORE_ID), '') AS store_id,
            NULLIF(TRIM(SUB_CATEGORY), '') AS sub_category,
            NULLIF(TRIM(VERSION_ID), '') AS version_id,
            NULLIF(TRIM(DAILY_VISITS), '') AS daily_visits_text,
            NULLIF(TRIM(LOCAL_DATE), '') AS local_date_text
        FROM raw_store_visits
        """
    )


def collect_raw_quality(connection: duckdb.DuckDBPyConnection) -> dict[str, Any]:
    missing_expressions = ",\n".join(
        f"COUNT_IF({column.lower() if column != 'SUB_CATEGORY' else 'sub_category'} IS NULL) "
        f"AS missing_{column.lower()}"
        for column in EXPECTED_COLUMNS
        if column not in {"DAILY_VISITS", "LOCAL_DATE"}
    )
    query = f"""
        SELECT
            COUNT(*) AS raw_rows,
            {missing_expressions},
            COUNT_IF(daily_visits_text IS NULL) AS missing_daily_visits,
            COUNT_IF(local_date_text IS NULL) AS missing_local_date,
            COUNT_IF(daily_visits_text IS NOT NULL AND daily_visits IS NULL)
                AS invalid_daily_visits,
            COUNT_IF(local_date_text IS NOT NULL AND local_date IS NULL)
                AS invalid_local_date,
            COUNT_IF(daily_visits < 0) AS negative_daily_visits,
            COUNT_IF(daily_visits = 0) AS zero_daily_visits,
            COUNT_IF(local_date > CURRENT_DATE) AS future_dates,
            COUNT_IF(state IS NOT NULL AND NOT REGEXP_FULL_MATCH(state, '[A-Z]{{2}}'))
                AS suspicious_state_values,
            COUNT_IF(naics_code IS NOT NULL AND NOT REGEXP_FULL_MATCH(naics_code, '[0-9]{{6}}'))
                AS suspicious_naics_values,
            MIN(local_date) AS earliest_valid_date,
            MAX(local_date) AS latest_valid_date,
            MIN(daily_visits) FILTER (WHERE daily_visits >= 0) AS minimum_valid_visits,
            MAX(daily_visits) FILTER (WHERE daily_visits >= 0) AS maximum_valid_visits,
            APPROX_QUANTILE(daily_visits, 0.999)
                FILTER (WHERE daily_visits >= 0) AS high_visit_threshold,
            COUNT_IF(
                store_id IS NOT NULL
                AND local_date IS NOT NULL
                AND daily_visits IS NOT NULL
                AND daily_visits >= 0
            ) AS valid_rows_before_deduplication
        FROM typed_store_visits
    """
    cursor = connection.execute(query)
    columns = [item[0] for item in cursor.description]
    return dict(zip(columns, cursor.fetchone(), strict=True))


def clean_candidate_query(high_visit_threshold: int) -> str:
    return f"""
        SELECT
            store_id,
            name,
            brand,
            category,
            sub_category,
            naics_code,
            local_date,
            daily_visits,
            state,
            market,
            stock_exchange,
            stock_symbol,
            version_id,
            daily_visits = 0 AS is_zero_visits,
            daily_visits > {int(high_visit_threshold)} AS is_suspicious_high_visits,
            'derived' AS data_type
        FROM typed_store_visits
        WHERE store_id IS NOT NULL
          AND local_date IS NOT NULL
          AND daily_visits IS NOT NULL
          AND daily_visits >= 0
    """


def recover_candidate_threshold(
    connection: duckdb.DuckDBPyConnection,
    candidate_path: Path,
    fallback_threshold: int,
) -> int:
    """Recover the effective flag boundary when resuming a written candidate."""
    candidate = f"read_parquet({sql_literal(candidate_path.as_posix())})"
    maximum_unflagged, minimum_flagged = connection.execute(
        f"""
        SELECT
            MAX(daily_visits) FILTER (WHERE NOT is_suspicious_high_visits),
            MIN(daily_visits) FILTER (WHERE is_suspicious_high_visits)
        FROM {candidate}
        """
    ).fetchone()
    if maximum_unflagged is None or minimum_flagged is None:
        return int(fallback_threshold)
    if int(minimum_flagged) <= int(maximum_unflagged):
        raise ValueError("Candidate high-visit flags do not have a valid boundary.")
    return int(maximum_unflagged)


def write_parquet(
    connection: duckdb.DuckDBPyConnection,
    query: str,
    destination: Path,
) -> None:
    connection.execute(
        f"COPY ({query}) TO {sql_literal(destination.as_posix())} "
        "(FORMAT PARQUET, COMPRESSION ZSTD, ROW_GROUP_SIZE 122880)"
    )


def remove_exact_duplicates(
    connection: duckdb.DuckDBPyConnection,
    candidate_path: Path,
    clean_path: Path,
) -> tuple[int, int]:
    candidate = f"read_parquet({sql_literal(candidate_path.as_posix())})"
    candidate_rows = connection.execute(f"SELECT COUNT(*) FROM {candidate}").fetchone()[0]
    bucket_root = candidate_path.parent / "duplicate_buckets"
    clean_parts = candidate_path.parent / "deduplicated_parts"
    if bucket_root.exists():
        shutil.rmtree(bucket_root)
    if clean_parts.exists():
        shutil.rmtree(clean_parts)

    hash_expression = "HASH(" + ", ".join(
        [
            "store_id",
            "name",
            "brand",
            "category",
            "sub_category",
            "naics_code",
            "local_date",
            "daily_visits",
            "state",
            "market",
            "stock_exchange",
            "stock_symbol",
            "version_id",
            "is_zero_visits",
            "is_suspicious_high_visits",
            "data_type",
        ]
    ) + ")"
    connection.execute(
        f"""
        COPY (
            SELECT *, ({hash_expression} % {DUPLICATE_BUCKET_COUNT})::INTEGER
                AS duplicate_bucket
            FROM {candidate}
        ) TO {sql_literal(bucket_root.as_posix())}
        (
            FORMAT PARQUET,
            COMPRESSION ZSTD,
            PARTITION_BY (duplicate_bucket),
            ROW_GROUP_SIZE 122880,
            OVERWRITE_OR_IGNORE
        )
        """
    )

    bucket_directories = sorted(
        bucket_root.glob("duplicate_bucket=*"),
        key=lambda path: int(path.name.split("=", 1)[1]),
    )
    if not bucket_directories:
        raise ValueError("Duplicate partitioning produced no buckets.")

    duplicates = 0
    for bucket_directory in bucket_directories:
        bucket_glob = (bucket_directory / "*.parquet").as_posix()
        bucket = (
            f"read_parquet({sql_literal(bucket_glob)}, hive_partitioning = false)"
        )
        bucket_duplicates = connection.execute(
            f"""
            SELECT COALESCE(SUM(group_size - 1), 0)::BIGINT
            FROM (
                SELECT *, COUNT(*) AS group_size
                FROM {bucket}
                GROUP BY ALL
                HAVING COUNT(*) > 1
            )
            """
        ).fetchone()[0]
        duplicates += int(bucket_duplicates)

    if duplicates:
        clean_parts.mkdir()
        for index, bucket_directory in enumerate(bucket_directories):
            bucket_glob = (bucket_directory / "*.parquet").as_posix()
            part_path = clean_parts / f"part_{index:04d}.parquet"
            write_parquet(
                connection,
                f"SELECT DISTINCT * FROM read_parquet("
                f"{sql_literal(bucket_glob)}, hive_partitioning = false)",
                part_path,
            )
        parts_glob = (clean_parts / "*.parquet").as_posix()
        write_parquet(
            connection,
            f"SELECT * FROM read_parquet({sql_literal(parts_glob)})",
            clean_path,
        )
        candidate_path.unlink()
        clean_rows = candidate_rows - duplicates
    else:
        candidate_path.replace(clean_path)
        clean_rows = candidate_rows

    shutil.rmtree(bucket_root)
    if clean_parts.exists():
        shutil.rmtree(clean_parts)
    return int(duplicates), int(clean_rows)


def copy_csv(
    connection: duckdb.DuckDBPyConnection,
    query: str,
    destination: Path,
) -> None:
    connection.execute(
        f"COPY ({query}) TO {sql_literal(destination.as_posix())} (FORMAT CSV, HEADER)"
    )


def write_single_row_csv(destination: Path, row: dict[str, Any]) -> None:
    """Write one already-calculated result row without rerunning its SQL."""
    with destination.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(row))
        writer.writeheader()
        writer.writerow(row)


def create_summary_tables(
    connection: duckdb.DuckDBPyConnection,
    clean_path: Path,
    summary_dir: Path,
    high_visit_threshold: int,
) -> dict[str, Any]:
    clean = f"read_parquet({sql_literal(clean_path.as_posix())})"

    percentile_cursor = connection.execute(
        f"""
        SELECT
            APPROX_QUANTILE(daily_visits, 0.25) AS p25,
            APPROX_QUANTILE(daily_visits, 0.50) AS p50,
            APPROX_QUANTILE(daily_visits, 0.75) AS p75,
            APPROX_QUANTILE(daily_visits, 0.95) AS p95,
            APPROX_QUANTILE(daily_visits, 0.99) AS p99
        FROM {clean}
        """
    )
    percentile_columns = [item[0] for item in percentile_cursor.description]
    percentiles = dict(
        zip(percentile_columns, percentile_cursor.fetchone(), strict=True)
    )
    percentiles["p999"] = int(high_visit_threshold)
    percentiles["data_type"] = "derived"
    write_single_row_csv(summary_dir / "visit_percentiles.csv", percentiles)

    summary_query = f"""
        SELECT
            COUNT(*) AS total_rows,
            COUNT(DISTINCT store_id) AS unique_stores,
            COUNT(DISTINCT brand) AS unique_brands,
            COUNT(DISTINCT category) AS unique_categories,
            COUNT(DISTINCT market) AS unique_markets,
            COUNT(DISTINCT local_date) AS unique_dates,
            MIN(local_date) AS earliest_date,
            MAX(local_date) AS latest_date,
            SUM(daily_visits) AS total_visits,
            ROUND(AVG(daily_visits), 2) AS mean_daily_visits,
            {int(percentiles['p50'])} AS approximate_median_daily_visits,
            MIN(daily_visits) AS minimum_daily_visits,
            MAX(daily_visits) AS maximum_daily_visits,
            ROUND(STDDEV_SAMP(daily_visits), 2) AS standard_deviation_daily_visits,
            COUNT_IF(is_zero_visits) AS zero_visit_rows,
            COUNT_IF(is_suspicious_high_visits) AS suspicious_high_visit_rows,
            'derived' AS data_type
        FROM {clean}
    """
    cursor = connection.execute(summary_query)
    columns = [item[0] for item in cursor.description]
    summary = dict(zip(columns, cursor.fetchone(), strict=True))
    write_single_row_csv(summary_dir / "summary_statistics.csv", summary)

    copy_csv(
        connection,
        f"""
        SELECT
            brand,
            SUM(daily_visits) AS total_visits,
            COUNT(*) AS record_count,
            COUNT(DISTINCT store_id) AS unique_stores,
            ROUND(AVG(daily_visits), 2) AS mean_daily_visits,
            MIN(local_date) AS earliest_date,
            MAX(local_date) AS latest_date,
            'derived' AS data_type
        FROM {clean}
        GROUP BY brand
        ORDER BY total_visits DESC NULLS LAST, brand
        """,
        summary_dir / "visits_by_brand.csv",
    )

    copy_csv(
        connection,
        f"""
        SELECT
            category,
            SUM(daily_visits) AS total_visits,
            COUNT(*) AS record_count,
            COUNT(DISTINCT store_id) AS unique_stores,
            ROUND(AVG(daily_visits), 2) AS mean_daily_visits,
            'derived' AS data_type
        FROM {clean}
        GROUP BY category
        ORDER BY total_visits DESC NULLS LAST, category
        """,
        summary_dir / "visits_by_category.csv",
    )

    copy_csv(
        connection,
        f"""
        SELECT
            market,
            SUM(daily_visits) AS total_visits,
            COUNT(*) AS record_count,
            COUNT(DISTINCT store_id) AS unique_stores,
            ROUND(AVG(daily_visits), 2) AS mean_daily_visits,
            'derived' AS data_type
        FROM {clean}
        GROUP BY market
        ORDER BY total_visits DESC NULLS LAST, market
        """,
        summary_dir / "visits_by_market.csv",
    )

    copy_csv(
        connection,
        f"""
        SELECT
            EXTRACT(ISODOW FROM local_date)::INTEGER AS weekday_number,
            DAYNAME(local_date) AS weekday,
            EXTRACT(ISODOW FROM local_date) IN (6, 7) AS is_weekend,
            SUM(daily_visits) AS total_visits,
            COUNT(*) AS record_count,
            COUNT(DISTINCT store_id) AS unique_stores,
            ROUND(AVG(daily_visits), 2) AS mean_daily_visits,
            'derived' AS data_type
        FROM {clean}
        GROUP BY weekday_number, weekday, is_weekend
        ORDER BY weekday_number
        """,
        summary_dir / "weekday_patterns.csv",
    )

    copy_csv(
        connection,
        f"""
        SELECT
            DATE_TRUNC('month', local_date)::DATE AS month,
            SUM(daily_visits) AS total_visits,
            COUNT(*) AS record_count,
            COUNT(DISTINCT store_id) AS unique_stores,
            ROUND(AVG(daily_visits), 2) AS mean_daily_visits,
            'derived' AS data_type
        FROM {clean}
        GROUP BY month
        ORDER BY month
        """,
        summary_dir / "monthly_trends.csv",
    )
    return summary


def duplicate_store_date_metrics(
    connection: duckdb.DuckDBPyConnection,
    clean_path: Path,
) -> tuple[int, int]:
    clean = f"read_parquet({sql_literal(clean_path.as_posix())})"
    row = connection.execute(
        f"""
        SELECT
            COUNT(*)::BIGINT AS duplicate_groups,
            COALESCE(SUM(group_size - 1), 0)::BIGINT AS extra_rows
        FROM (
            SELECT store_id, local_date, COUNT(*) AS group_size
            FROM {clean}
            GROUP BY store_id, local_date
            HAVING COUNT(*) > 1
        )
        """
    ).fetchone()
    return int(row[0]), int(row[1])


def missing_counts_from_quality(quality: dict[str, Any]) -> list[tuple[str, int]]:
    rows = []
    for column in EXPECTED_COLUMNS:
        key = f"missing_{column.lower()}"
        rows.append((column, int(quality[key])))
    return rows


def format_value(value: Any) -> str:
    if value is None:
        return "n/a"
    if isinstance(value, float):
        return f"{value:,.2f}"
    if isinstance(value, int):
        return f"{value:,}"
    return str(value)


def write_quality_report(
    path: Path,
    files: list[Path],
    quality: dict[str, Any],
    summary: dict[str, Any],
    exact_duplicates: int,
    duplicate_store_date_groups: int,
    duplicate_store_date_extra_rows: int,
    limited_run: bool,
) -> None:
    raw_rows = int(quality["raw_rows"])
    missing_table = ["| Column | Missing rows | Missing percent |", "| --- | ---: | ---: |"]
    for column, count in missing_counts_from_quality(quality):
        percentage = (count / raw_rows * 100) if raw_rows else 0
        missing_table.append(f"| `{column}` | {count:,} | {percentage:.3f}% |")

    excluded = int(quality["valid_rows_before_deduplication"])
    excluded = raw_rows - excluded
    generated_at = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    scope = "LIMITED TEST RUN" if limited_run else "COMPLETE SOURCE RUN"

    report = f"""# Store Visits Data-Quality Report

## Run scope

- Scope: **{scope}**
- Generated: `{generated_at}`
- Source files: {len(files)}
- Raw rows inspected: {raw_rows:,}
- Clean rows written: {int(summary['total_rows']):,}
- Data label: `derived`

## Cleaning decisions

- Trim surrounding whitespace from text fields.
- Convert blank strings to null values.
- Parse `LOCAL_DATE` strictly as `YYYY-MM-DD`.
- Parse `DAILY_VISITS` only when it is a whole integer.
- Standardize state, stock exchange, and stock symbol values to uppercase.
- Exclude rows missing `STORE_ID`, a valid date, or a valid visit count.
- Exclude negative visit counts.
- Remove exact duplicate rows after normalization.
- Retain zero visits and flag them with `is_zero_visits`.
- Retain values above the approximate 99.9th percentile and flag them with
  `is_suspicious_high_visits`; high values are review candidates, not automatic errors.
- Retain non-identical duplicate store-date records and report them for later review.

## Quality checks

| Check | Result |
| --- | ---: |
| Rows excluded for missing/invalid required fields or negative visits | {excluded:,} |
| Invalid nonblank dates | {int(quality['invalid_local_date']):,} |
| Invalid nonblank visit values | {int(quality['invalid_daily_visits']):,} |
| Negative visit rows | {int(quality['negative_daily_visits']):,} |
| Zero-visit rows in raw input | {int(quality['zero_daily_visits']):,} |
| Exact normalized duplicate rows removed | {exact_duplicates:,} |
| Duplicate store-date groups retained | {duplicate_store_date_groups:,} |
| Extra rows within duplicate store-date groups | {duplicate_store_date_extra_rows:,} |
| Future-dated rows | {int(quality['future_dates']):,} |
| Suspicious state-format rows | {int(quality['suspicious_state_values']):,} |
| Suspicious NAICS-format rows | {int(quality['suspicious_naics_values']):,} |
| Approximate high-visit review threshold | > {format_value(quality['high_visit_threshold'])} |
| High-visit rows retained and flagged | {int(summary['suspicious_high_visit_rows']):,} |
| Earliest / latest valid date | {quality['earliest_valid_date']} / {quality['latest_valid_date']} |
| Minimum / maximum nonnegative visits | {format_value(quality['minimum_valid_visits'])} / {format_value(quality['maximum_valid_visits'])} |

## Missing values in raw input

{chr(10).join(missing_table)}

## Important summary statistics

| Metric | Result |
| --- | ---: |
| Unique stores | {int(summary['unique_stores']):,} |
| Unique brands | {int(summary['unique_brands']):,} |
| Unique categories | {int(summary['unique_categories']):,} |
| Unique markets | {int(summary['unique_markets']):,} |
| Total visits | {int(summary['total_visits']):,} |
| Mean daily visits | {format_value(summary['mean_daily_visits'])} |
| Approximate median daily visits | {format_value(summary['approximate_median_daily_visits'])} |
| Standard deviation | {format_value(summary['standard_deviation_daily_visits'])} |

## Interpretation and limitations

The output is suitable for relative historical commercial-activity analysis. It is not
measured World Cup attendance, pedestrian flow, transit ridership, or an exact future
forecast. Approximate quantiles are used because the dataset is very large. A duplicate
`STORE_ID` plus `LOCAL_DATE` is not automatically deleted when other fields differ;
those records require a business-rule decision with the team.
"""
    path.write_text(report, encoding="utf-8")


def promote_outputs(work_root: Path, output_root: Path, overwrite: bool) -> None:
    pairs = [
        (
            work_root / "processed" / "store_visits_clean.parquet",
            output_root / "processed" / "store_visits_clean.parquet",
        ),
        *[
            (work_root / "summaries" / name, output_root / "summaries" / name)
            for name in SUMMARY_FILENAMES
        ],
    ]
    for source, destination in pairs:
        destination.parent.mkdir(parents=True, exist_ok=True)
        if destination.exists():
            if not overwrite:
                raise FileExistsError(f"Output already exists: {destination}")
            destination.unlink()
        source.replace(destination)
    shutil.rmtree(work_root)
    duckdb_temp = output_root / "duckdb_tmp"
    if duckdb_temp.exists() and not any(duckdb_temp.iterdir()):
        duckdb_temp.rmdir()


def run_pipeline(args: argparse.Namespace) -> dict[str, Any]:
    ensure_safe_options(args)
    files = discover_input_files(args.input)
    validate_headers(files)
    output_root = args.output_root.resolve()
    work_root = prepare_workspace(output_root, args.overwrite, args.resume)
    work_processed = work_root / "processed"
    work_summaries = work_root / "summaries"
    candidate_path = work_processed / "store_visits_clean_candidate.parquet"
    clean_path = work_processed / "store_visits_clean.parquet"

    print(f"Validated {len(files)} source file(s).", flush=True)
    connection = duckdb.connect()
    try:
        configure_connection(
            connection, output_root, args.threads, args.memory_limit
        )
        create_source_views(connection, files, args.limit)

        print("Checking missing values, dates, numeric values, and suspicious values...", flush=True)
        quality = collect_raw_quality(connection)
        threshold = quality["high_visit_threshold"]
        if threshold is None:
            raise ValueError("No valid nonnegative DAILY_VISITS values were found.")

        if args.resume:
            print("Reusing the completed clean candidate Parquet...", flush=True)
            threshold = recover_candidate_threshold(
                connection, candidate_path, int(threshold)
            )
            quality["high_visit_threshold"] = threshold
        else:
            print("Writing typed clean candidate Parquet...", flush=True)
            write_parquet(
                connection,
                clean_candidate_query(int(threshold)),
                candidate_path,
            )

        print("Checking and removing exact normalized duplicates...", flush=True)
        exact_duplicates, clean_rows = remove_exact_duplicates(
            connection, candidate_path, clean_path
        )
        if clean_rows == 0:
            raise ValueError("Cleaning produced zero rows; outputs were not promoted.")

        print("Calculating summary tables...", flush=True)
        summary = create_summary_tables(
            connection, clean_path, work_summaries, int(threshold)
        )

        print("Checking duplicate store-date records...", flush=True)
        duplicate_groups, duplicate_extra_rows = duplicate_store_date_metrics(
            connection, clean_path
        )

        write_quality_report(
            work_summaries / "data_quality_report.md",
            files,
            quality,
            summary,
            exact_duplicates,
            duplicate_groups,
            duplicate_extra_rows,
            limited_run=args.limit is not None,
        )
    finally:
        connection.close()

    promote_outputs(work_root, output_root, args.overwrite)
    result = {
        "scope": "limited test" if args.limit is not None else "complete source",
        "source_files": len(files),
        "raw_rows": int(quality["raw_rows"]),
        "clean_rows": int(summary["total_rows"]),
        "exact_duplicates_removed": exact_duplicates,
        "duplicate_store_date_groups": duplicate_groups,
        "clean_dataset": str(
            (output_root / "processed" / "store_visits_clean.parquet").resolve()
        ),
        "quality_report": str(
            (output_root / "summaries" / "data_quality_report.md").resolve()
        ),
        "summary_directory": str((output_root / "summaries").resolve()),
    }
    print(json.dumps(result, indent=2), flush=True)
    return result


def main(argv: list[str] | None = None) -> int:
    try:
        run_pipeline(parse_args(argv))
    except (FileNotFoundError, FileExistsError, OSError, ValueError) as error:
        print(f"Error: {error}", flush=True)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
