"""Focused tests for the reusable store-visit cleaning pipeline."""

from __future__ import annotations

import csv
import json
import tempfile
import unittest
from pathlib import Path

import duckdb

from scripts.data.clean_store_visits import (
    EXPECTED_COLUMNS,
    create_source_views,
    exact_visit_percentiles,
    parse_args,
    run_pipeline,
)


def write_fixture(path: Path, rows: list[list[str]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.writer(stream)
        writer.writerow(EXPECTED_COLUMNS)
        writer.writerows(rows)


class CleanStoreVisitsTests(unittest.TestCase):
    def test_exact_percentiles_use_discrete_nearest_rank(self) -> None:
        connection = duckdb.connect()
        try:
            connection.execute(
                "CREATE TEMP TABLE visits(daily_visits BIGINT)"
            )
            connection.execute(
                "INSERT INTO visits VALUES (0), (1), (1), (2), (100)"
            )
            result = exact_visit_percentiles(connection, "visits")
        finally:
            connection.close()

        self.assertEqual(
            result,
            {"p25": 1, "p50": 1, "p75": 2, "p95": 100, "p99": 100, "p999": 100},
        )

    def test_limited_source_is_materialized_once(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            csv_path = Path(temp_dir) / "sample.csv"
            rows = [
                ["B", "C", str(value), "2024-01-01", "M", "111111", "N", "TX", "", "", f"S{value}", "SC", "9.0"]
                for value in range(5)
            ]
            write_fixture(csv_path, rows)
            connection = duckdb.connect()
            try:
                create_source_views(connection, [csv_path], limit=2)
                csv_path.unlink()
                raw_count = connection.execute(
                    "SELECT COUNT(*) FROM raw_store_visits"
                ).fetchone()[0]
                typed_count = connection.execute(
                    "SELECT COUNT(*) FROM typed_store_visits"
                ).fetchone()[0]
            finally:
                connection.close()

        self.assertEqual(raw_count, 2)
        self.assertEqual(typed_count, 2)

    def test_end_to_end_quality_checks_and_outputs(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            csv_path = temp_path / "store_visits.csv"
            output_root = temp_path / "output"
            base = ["Brand", "Category", "", "", "Market", "1111", "Name", "tx", "", "", "S1", "", "9.0"]
            zero = base.copy()
            zero[2], zero[3] = "0", "2024-01-01"
            same_store_date = base.copy()
            same_store_date[2], same_store_date[3] = "5", "2024-01-01"
            valid_100 = base.copy()
            valid_100[2], valid_100[3], valid_100[5], valid_100[10], valid_100[11] = (
                "100", "2024-01-02", "31135", "S2", "Detailed"
            )
            valid_10 = base.copy()
            valid_10[2], valid_10[3], valid_10[5], valid_10[10], valid_10[11] = (
                "10", "2024-01-03", "722511", "S3", "Detailed"
            )
            missing_store = valid_10.copy()
            missing_store[10] = ""
            invalid_date = valid_10.copy()
            invalid_date[3], invalid_date[10] = "01/04/2024", "S4"
            invalid_visits = valid_10.copy()
            invalid_visits[2], invalid_visits[10] = "ten", "S5"
            negative_visits = valid_10.copy()
            negative_visits[2], negative_visits[10] = "-1", "S6"
            write_fixture(
                csv_path,
                [
                    zero,
                    zero.copy(),
                    same_store_date,
                    valid_100,
                    valid_10,
                    missing_store,
                    invalid_date,
                    invalid_visits,
                    negative_visits,
                ],
            )

            result = run_pipeline(
                parse_args(
                    [
                        "--input",
                        str(csv_path),
                        "--output-root",
                        str(output_root),
                        "--threads",
                        "1",
                        "--memory-limit",
                        "256MB",
                        "--temp-limit",
                        "100MB",
                    ]
                )
            )

            clean_path = output_root / "processed" / "store_visits_clean.parquet"
            clean_metrics = duckdb.connect().execute(
                """
                SELECT
                    COUNT(*),
                    COUNT_IF(is_zero_visits),
                    COUNT_IF(is_suspicious_high_visits),
                    COUNT_IF(state = 'TX')
                FROM read_parquet(?)
                """,
                [str(clean_path)],
            ).fetchone()
            with (output_root / "summaries" / "visit_percentiles.csv").open(
                encoding="utf-8", newline=""
            ) as stream:
                percentiles = next(csv.DictReader(stream))
            report = (output_root / "summaries" / "data_quality_report.md").read_text(
                encoding="utf-8"
            )
            metadata = json.loads(
                (output_root / "summaries" / "run_metadata.json").read_text(
                    encoding="utf-8"
                )
            )

        self.assertEqual(result["raw_rows"], 9)
        self.assertEqual(result["clean_rows"], 4)
        self.assertEqual(result["exact_duplicates_removed"], 1)
        self.assertEqual(result["duplicate_store_date_groups"], 1)
        self.assertEqual(clean_metrics, (4, 1, 0, 4))
        self.assertEqual(
            {key: percentiles[key] for key in ("p25", "p50", "p75", "p95", "p99", "p999")},
            {"p25": "0", "p50": "5", "p75": "10", "p95": "100", "p99": "100", "p999": "100"},
        )
        self.assertIn("NAICS classification granularity", report)
        self.assertNotIn("Suspicious NAICS-format", report)
        self.assertIn("Invalid nonblank dates | 1", report)
        self.assertIn("Invalid nonblank visit values | 1", report)
        self.assertIn("Negative visit rows | 1", report)
        self.assertEqual(len(metadata["pipeline_sha256"]), 64)


if __name__ == "__main__":
    unittest.main()
