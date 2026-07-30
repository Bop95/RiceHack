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
data/summaries/run_metadata.json
"""

from __future__ import annotations

import argparse
import csv
import glob
import gzip
import hashlib
import json
import platform
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
    "run_metadata.json",
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
        "--temp-limit",
        default="20GB",
        help="Maximum DuckDB temporary-disk use such as 10GB (default: 20GB).",
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
    if not MEMORY_PATTERN.fullmatch(args.temp_limit):
        raise ValueError("--temp-limit must look like 10GB or 8000MB.")
    if args.limit is not None and args.limit < 1:
        raise ValueError("--limit must be at least 1 when supplied.")
    if args.overwrite and args.resume:
        raise ValueError("Use either --overwrite or --resume, not both.")


def storage_size_bytes(value: str) -> int:
    """Convert the already-validated MB/GB option into decimal bytes."""
    if MEMORY_PATTERN.fullmatch(value) is None:
        raise ValueError(f"Invalid storage size: {value}")
    number = int(value[:-2])
    multiplier = 1_000_000_000 if value.upper().endswith("GB") else 1_000_000
    return number * multiplier


def check_temporary_disk_space(output_root: Path, temp_limit: str) -> None:
    """Fail early when the configured spill allowance exceeds free disk space."""
    probe = output_root.resolve()
    while not probe.exists() and probe != probe.parent:
        probe = probe.parent
    free_bytes = shutil.disk_usage(probe).free
    required_bytes = storage_size_bytes(temp_limit)
    if free_bytes < required_bytes:
        raise OSError(
            f"Only {free_bytes / 1_000_000_000:.1f} GB is free near {output_root}, "
            f"below --temp-limit {temp_limit}. Choose a smaller safe limit or free disk."
        )


def input_fingerprint(files: list[Path]) -> list[dict[str, Any]]:
    """Record enough source metadata to reject an unsafe resume."""
    return [
        {
            "path": path.as_posix(),
            "size_bytes": path.stat().st_size,
            "modified_time_ns": path.stat().st_mtime_ns,
        }
        for path in files
    ]


def base_run_metadata(
    files: list[Path],
    args: argparse.Namespace,
    percentiles: dict[str, int],
) -> dict[str, Any]:
    script_path = Path(__file__).resolve()
    return {
        "pipeline": script_path.name,
        "pipeline_sha256": hashlib.sha256(script_path.read_bytes()).hexdigest(),
        "input_files": input_fingerprint(files),
        "parameters": {
            "limit": args.limit,
            "threads": args.threads,
            "memory_limit": args.memory_limit.upper(),
            "temp_limit": args.temp_limit.upper(),
        },
        "software": {
            "python": platform.python_version(),
            "duckdb": duckdb.__version__,
        },
        "exact_visit_percentiles_before_deduplication": percentiles,
        "high_visit_threshold": percentiles["p999"],
    }


def validate_resume_metadata(
    path: Path,
    expected: dict[str, Any],
) -> None:
    if not path.exists():
        raise FileNotFoundError(
            f"--resume requires the run manifest created with the candidate: {path}"
        )
    saved = json.loads(path.read_text(encoding="utf-8"))
    checks = [
        ("input_files", saved.get("input_files"), expected["input_files"]),
        (
            "limit",
            saved.get("parameters", {}).get("limit"),
            expected["parameters"]["limit"],
        ),
        (
            "high_visit_threshold",
            saved.get("high_visit_threshold"),
            expected["high_visit_threshold"],
        ),
    ]
    for label, saved_value, expected_value in checks:
        if saved_value != expected_value:
            raise ValueError(
                f"Cannot resume: saved {label} does not match the current run."
            )


def expected_output_paths(output_root: Path) -> list[Path]:
    return [
        output_root / "processed" / "store_visits_clean.parquet",
        *[output_root / "summaries" / name for name in SUMMARY_FILENAMES],
    ]


def prepare_workspace(output_root: Path, overwrite: bool, resume: bool) -> Path:
    outputs = expected_output_paths(output_root)
    existing = [path for path in outputs if path.exists()]
    if existing and not (overwrite or resume):
        raise FileExistsError(
            f"Output already exists: {existing[0]}. Use --overwrite to replace outputs."
        )

    work_root = output_root / ".store_visits_work"
    if resume:
        candidate = work_root / "processed" / "store_visits_clean_candidate.parquet"
        clean = work_root / "processed" / "store_visits_clean.parquet"
        manifest = work_root / "run_manifest.json"
        if candidate.exists() == clean.exists() or not manifest.exists():
            raise FileNotFoundError(
                "--resume requires exactly one candidate/clean work Parquet plus its "
                f"run manifest under {work_root}."
            )
        (work_root / "summaries").mkdir(parents=True, exist_ok=True)
        for name in SUMMARY_FILENAMES:
            partial = work_root / "summaries" / name
            if partial.exists():
                partial.unlink()
        duckdb_temp = output_root / "duckdb_tmp"
        if duckdb_temp.exists():
            shutil.rmtree(duckdb_temp)
        duckdb_temp.mkdir(parents=True)
        return work_root

    if work_root.exists():
        if not overwrite:
            raise FileExistsError(
                f"Previous work directory exists: {work_root}. Use --overwrite after review."
            )
        shutil.rmtree(work_root)
    (work_root / "processed").mkdir(parents=True)
    (work_root / "summaries").mkdir(parents=True)
    duckdb_temp = output_root / "duckdb_tmp"
    if duckdb_temp.exists():
        shutil.rmtree(duckdb_temp)
    duckdb_temp.mkdir(parents=True)
    return work_root


def configure_connection(
    connection: duckdb.DuckDBPyConnection,
    output_root: Path,
    threads: int,
    memory_limit: str,
    temp_limit: str,
) -> None:
    connection.execute(f"SET threads = {threads}")
    connection.execute(f"SET memory_limit = {sql_literal(memory_limit.upper())}")
    connection.execute("SET preserve_insertion_order = false")
    connection.execute(
        f"SET max_temp_directory_size = {sql_literal(temp_limit.upper())}"
    )
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
        # A table freezes one sample for every downstream check. A view would
        # rescan the unordered LIMIT and could give different rows per query.
        connection.execute("SET preserve_insertion_order = true")
        connection.execute(f"CREATE TEMP TABLE raw_store_visits AS {source}")
        connection.execute("SET preserve_insertion_order = false")
    else:
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
            COUNT_IF(naics_code IS NOT NULL AND LENGTH(naics_code) = 4)
                AS naics_4_digit_rows,
            COUNT_IF(
                naics_code IS NOT NULL
                AND LENGTH(naics_code) = 4
                AND sub_category IS NULL
            ) AS naics_4_digit_missing_sub_category_rows,
            COUNT_IF(naics_code IS NOT NULL AND LENGTH(naics_code) = 5)
                AS naics_5_digit_rows,
            COUNT_IF(naics_code IS NOT NULL AND LENGTH(naics_code) = 6)
                AS naics_6_digit_rows,
            COUNT_IF(
                naics_code IS NOT NULL AND LENGTH(naics_code) NOT IN (4, 5, 6)
            ) AS naics_other_length_rows,
            MIN(local_date) AS earliest_valid_date,
            MAX(local_date) AS latest_valid_date,
            MIN(daily_visits) FILTER (WHERE daily_visits >= 0) AS minimum_valid_visits,
            MAX(daily_visits) FILTER (WHERE daily_visits >= 0) AS maximum_valid_visits,
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


def exact_visit_percentiles(
    connection: duckdb.DuckDBPyConnection,
    relation: str,
    where_clause: str = "TRUE",
) -> dict[str, int]:
    """Calculate discrete nearest-rank percentiles from a compact histogram."""
    probabilities = {
        "p25": 0.25,
        "p50": 0.50,
        "p75": 0.75,
        "p95": 0.95,
        "p99": 0.99,
        "p999": 0.999,
    }
    expressions = ",\n".join(
        f"MIN(value) FILTER (WHERE cumulative_count >= "
        f"CEIL(total_count * {probability})) AS {name}"
        for name, probability in probabilities.items()
    )
    cursor = connection.execute(
        f"""
        WITH histogram AS (
            SELECT daily_visits AS value, COUNT(*)::BIGINT AS frequency
            FROM {relation}
            WHERE {where_clause}
            GROUP BY daily_visits
        ),
        cumulative AS (
            SELECT
                value,
                SUM(frequency) OVER (
                    ORDER BY value ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
                ) AS cumulative_count,
                SUM(frequency) OVER () AS total_count
            FROM histogram
        )
        SELECT {expressions}
        FROM cumulative
        """
    )
    columns = [item[0] for item in cursor.description]
    row = cursor.fetchone()
    if row is None or any(value is None for value in row):
        raise ValueError("No valid DAILY_VISITS values were found for percentiles.")
    return {
        name: int(value)
        for name, value in zip(columns, row, strict=True)
    }


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
    percentiles = exact_visit_percentiles(connection, clean)
    percentile_output: dict[str, Any] = {
        **percentiles,
        "high_visit_threshold": int(high_visit_threshold),
        "data_type": "derived",
    }
    write_single_row_csv(
        summary_dir / "visit_percentiles.csv", percentile_output
    )

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
            {int(percentiles['p50'])} AS median_daily_visits,
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
    bucket_root = clean_path.parent / "store_date_buckets"
    if bucket_root.exists():
        shutil.rmtree(bucket_root)
    connection.execute(
        f"""
        COPY (
            SELECT
                store_id,
                local_date,
                (HASH(store_id, local_date) % {DUPLICATE_BUCKET_COUNT})::INTEGER
                    AS store_date_bucket
            FROM {clean}
        ) TO {sql_literal(bucket_root.as_posix())}
        (
            FORMAT PARQUET,
            COMPRESSION ZSTD,
            PARTITION_BY (store_date_bucket),
            ROW_GROUP_SIZE 122880,
            OVERWRITE_OR_IGNORE
        )
        """
    )

    duplicate_groups = 0
    extra_rows = 0
    try:
        bucket_directories = sorted(
            bucket_root.glob("store_date_bucket=*"),
            key=lambda path: int(path.name.split("=", 1)[1]),
        )
        if not bucket_directories:
            raise ValueError("Store-date partitioning produced no buckets.")
        for bucket_directory in bucket_directories:
            bucket_glob = (bucket_directory / "*.parquet").as_posix()
            row = connection.execute(
                f"""
                SELECT
                    COUNT(*)::BIGINT AS duplicate_groups,
                    COALESCE(SUM(group_size - 1), 0)::BIGINT AS extra_rows
                FROM (
                    SELECT store_id, local_date, COUNT(*) AS group_size
                    FROM read_parquet(
                        {sql_literal(bucket_glob)}, hive_partitioning = false
                    )
                    GROUP BY store_id, local_date
                    HAVING COUNT(*) > 1
                )
                """
            ).fetchone()
            duplicate_groups += int(row[0])
            extra_rows += int(row[1])
    finally:
        if bucket_root.exists():
            shutil.rmtree(bucket_root)
    return duplicate_groups, extra_rows


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
    naics_rows = [
        ("4 digits", int(quality["naics_4_digit_rows"])),
        ("5 digits", int(quality["naics_5_digit_rows"])),
        ("6 digits", int(quality["naics_6_digit_rows"])),
        ("Other lengths", int(quality["naics_other_length_rows"])),
    ]
    naics_table = [
        "| NAICS code length | Rows | Percent of inspected rows |",
        "| --- | ---: | ---: |",
    ]
    for label, count in naics_rows:
        percentage = (count / raw_rows * 100) if raw_rows else 0
        naics_table.append(f"| {label} | {count:,} | {percentage:.3f}% |")

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
- Retain values above the exact discrete 99.9th percentile and flag them with
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
| Exact high-visit review threshold (p99.9) | > {format_value(quality['high_visit_threshold'])} |
| High-visit rows retained and flagged | {int(summary['suspicious_high_visit_rows']):,} |
| Earliest / latest valid date | {quality['earliest_valid_date']} / {quality['latest_valid_date']} |
| Minimum / maximum nonnegative visits | {format_value(quality['minimum_valid_visits'])} / {format_value(quality['maximum_valid_visits'])} |

## Missing values after trimming

{chr(10).join(missing_table)}

## NAICS classification granularity

{chr(10).join(naics_table)}

The 4-, 5-, and 6-digit values are retained as classification levels, not labeled as
invalid. All {int(quality['naics_4_digit_missing_sub_category_rows']):,} inspected
4-digit rows also have a missing `SUB_CATEGORY`, which is consistent with a broader
classification level. The official dictionary is still needed to confirm this meaning.

## Important summary statistics

| Metric | Result |
| --- | ---: |
| Unique stores | {int(summary['unique_stores']):,} |
| Unique brands | {int(summary['unique_brands']):,} |
| Unique categories | {int(summary['unique_categories']):,} |
| Unique markets | {int(summary['unique_markets']):,} |
| Total visits | {int(summary['total_visits']):,} |
| Mean daily visits | {format_value(summary['mean_daily_visits'])} |
| Median daily visits | {format_value(summary['median_daily_visits'])} |
| Standard deviation | {format_value(summary['standard_deviation_daily_visits'])} |

## Interpretation and limitations

The output is suitable for relative historical commercial-activity analysis. It is not
measured World Cup attendance, pedestrian flow, transit ridership, or an exact future
forecast. Percentiles are exact discrete nearest-rank values calculated from a compact
visit-count histogram. A duplicate
`STORE_ID` plus `LOCAL_DATE` is not automatically deleted when other fields differ;
those records require a business-rule decision with the team.
"""
    path.write_text(report, encoding="utf-8")


def promote_outputs(work_root: Path, output_root: Path, overwrite: bool) -> None:
    summary_names = [
        name for name in SUMMARY_FILENAMES if name != "data_quality_report.md"
    ] + ["data_quality_report.md"]
    pairs = [
        (
            work_root / "processed" / "store_visits_clean.parquet",
            output_root / "processed" / "store_visits_clean.parquet",
        ),
        *[
            (work_root / "summaries" / name, output_root / "summaries" / name)
            for name in summary_names
        ],
    ]
    missing = [source for source, _ in pairs if not source.exists()]
    if missing:
        raise FileNotFoundError(f"Completed work output is missing: {missing[0]}")

    backup_root = work_root / "promotion_backup"
    backups: list[tuple[Path, Path]] = []
    promoted: list[tuple[Path, Path]] = []
    try:
        for _, destination in pairs:
            destination.parent.mkdir(parents=True, exist_ok=True)
            if destination.exists():
                if not overwrite:
                    raise FileExistsError(f"Output already exists: {destination}")
                relative = destination.relative_to(output_root)
                backup = backup_root / relative
                backup.parent.mkdir(parents=True, exist_ok=True)
                destination.replace(backup)
                backups.append((backup, destination))

        for source, destination in pairs:
            source.replace(destination)
            promoted.append((destination, source))
    except Exception:
        for destination, source in reversed(promoted):
            if destination.exists():
                source.parent.mkdir(parents=True, exist_ok=True)
                destination.replace(source)
        for backup, destination in reversed(backups):
            if backup.exists():
                destination.parent.mkdir(parents=True, exist_ok=True)
                backup.replace(destination)
        raise

    if backup_root.exists():
        shutil.rmtree(backup_root)
    shutil.rmtree(work_root)
    duckdb_temp = output_root / "duckdb_tmp"
    if duckdb_temp.exists() and not any(duckdb_temp.iterdir()):
        duckdb_temp.rmdir()


def run_pipeline(args: argparse.Namespace) -> dict[str, Any]:
    ensure_safe_options(args)
    files = discover_input_files(args.input)
    validate_headers(files)
    output_root = args.output_root.resolve()
    check_temporary_disk_space(output_root, args.temp_limit)
    work_root = prepare_workspace(output_root, args.overwrite, args.resume)
    work_processed = work_root / "processed"
    work_summaries = work_root / "summaries"
    candidate_path = work_processed / "store_visits_clean_candidate.parquet"
    clean_path = work_processed / "store_visits_clean.parquet"

    print(f"Validated {len(files)} source file(s).", flush=True)
    connection = duckdb.connect()
    try:
        configure_connection(
            connection,
            output_root,
            args.threads,
            args.memory_limit,
            args.temp_limit,
        )
        create_source_views(connection, files, args.limit)

        print("Checking missing values, dates, numeric values, and suspicious values...", flush=True)
        quality = collect_raw_quality(connection)
        raw_percentiles = exact_visit_percentiles(
            connection,
            "typed_store_visits",
            "daily_visits >= 0",
        )
        threshold = raw_percentiles["p999"]
        quality["high_visit_threshold"] = threshold
        run_metadata = base_run_metadata(files, args, raw_percentiles)
        manifest_path = work_root / "run_manifest.json"

        if args.resume:
            validate_resume_metadata(manifest_path, run_metadata)
            if clean_path.exists():
                print("Reusing the completed clean work Parquet...", flush=True)
                clean_rows = int(
                    connection.execute(
                        f"SELECT COUNT(*) FROM read_parquet("
                        f"{sql_literal(clean_path.as_posix())})"
                    ).fetchone()[0]
                )
                exact_duplicates = (
                    int(quality["valid_rows_before_deduplication"]) - clean_rows
                )
                if exact_duplicates < 0:
                    raise ValueError(
                        "Cannot resume: clean work has more rows than valid source input."
                    )
            else:
                print("Reusing the completed clean candidate Parquet...", flush=True)
                candidate_threshold = recover_candidate_threshold(
                    connection, candidate_path, threshold
                )
                if candidate_threshold != threshold:
                    raise ValueError(
                        "Cannot resume: candidate flags do not match the exact threshold."
                    )
                print("Checking and removing exact normalized duplicates...", flush=True)
                exact_duplicates, clean_rows = remove_exact_duplicates(
                    connection, candidate_path, clean_path
                )
        else:
            print("Writing typed clean candidate Parquet...", flush=True)
            write_parquet(
                connection,
                clean_candidate_query(threshold),
                candidate_path,
            )
            manifest_path.write_text(
                json.dumps(run_metadata, indent=2) + "\n", encoding="utf-8"
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
        run_metadata.update(
            {
                "completed_at_utc": datetime.now(timezone.utc)
                .isoformat()
                .replace("+00:00", "Z"),
                "scope": "limited test" if args.limit is not None else "complete source",
                "raw_rows": int(quality["raw_rows"]),
                "clean_rows": int(summary["total_rows"]),
                "exact_duplicates_removed": exact_duplicates,
                "duplicate_store_date_groups": duplicate_groups,
            }
        )
        (work_summaries / "run_metadata.json").write_text(
            json.dumps(run_metadata, indent=2) + "\n", encoding="utf-8"
        )
    finally:
        connection.close()

    promote_outputs(work_root, output_root, args.overwrite or args.resume)
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
    except (
        duckdb.Error,
        FileNotFoundError,
        FileExistsError,
        OSError,
        ValueError,
    ) as error:
        print(f"Error: {error}", flush=True)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
