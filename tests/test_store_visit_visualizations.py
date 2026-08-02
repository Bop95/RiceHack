"""Tests for the Step-3 store-visit visualization pipeline."""

from __future__ import annotations

import csv
import tempfile
import unittest
from pathlib import Path

import duckdb
from PIL import Image

from scripts.visualization.create_store_visit_charts import parse_args, run


def write_csv(path: Path, fieldnames: list[str], rows: list[list[object]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.writer(stream)
        writer.writerow(fieldnames)
        writer.writerows(rows)


class StoreVisitVisualizationTests(unittest.TestCase):
    def test_end_to_end_chart_generation(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            summaries = root / "summaries"
            reports = root / "reports"
            summaries.mkdir()

            write_csv(
                summaries / "visits_by_brand.csv",
                [
                    "brand",
                    "total_visits",
                    "record_count",
                    "unique_stores",
                    "mean_daily_visits",
                ],
                [
                    ["Brand A", 1000, 100, 10, 10],
                    ["Brand B", 800, 40, 4, 20],
                    ["Brand C", 500, 50, 5, 10],
                ],
            )
            write_csv(
                summaries / "visits_by_category.csv",
                [
                    "category",
                    "total_visits",
                    "record_count",
                    "unique_stores",
                    "mean_daily_visits",
                ],
                [
                    ["Category A", 2000, 100, 10, 20],
                    ["Category B", 1000, 25, 5, 40],
                    ["Category C", 500, 50, 5, 10],
                ],
            )
            write_csv(
                summaries / "visits_by_market.csv",
                [
                    "market",
                    "total_visits",
                    "record_count",
                    "unique_stores",
                    "mean_daily_visits",
                ],
                [
                    ["Market A", 3000, 100, 10, 30],
                    ["Market B", 2000, 40, 4, 50],
                ],
            )
            write_csv(
                summaries / "weekday_patterns.csv",
                [
                    "weekday_number",
                    "weekday",
                    "is_weekend",
                    "total_visits",
                    "record_count",
                    "mean_daily_visits",
                ],
                [
                    [1, "Monday", "false", 100, 10, 10],
                    [2, "Tuesday", "false", 110, 10, 11],
                    [3, "Wednesday", "false", 120, 10, 12],
                    [4, "Thursday", "false", 130, 10, 13],
                    [5, "Friday", "false", 150, 10, 15],
                    [6, "Saturday", "true", 180, 10, 18],
                    [7, "Sunday", "true", 140, 10, 14],
                ],
            )
            write_csv(
                summaries / "monthly_trends.csv",
                [
                    "month",
                    "total_visits",
                    "record_count",
                    "unique_stores",
                    "mean_daily_visits",
                ],
                [
                    ["2024-01-01", 1000, 100, 10, 10],
                    ["2024-02-01", 800, 100, 10, 8],
                    ["2024-03-01", 1200, 100, 10, 12],
                ],
            )
            write_csv(
                summaries / "summary_statistics.csv",
                [
                    "total_rows",
                    "total_visits",
                    "mean_daily_visits",
                    "median_daily_visits",
                    "zero_visit_rows",
                ],
                [[12, 66, 5.5, 5, 1]],
            )
            write_csv(
                summaries / "visit_percentiles.csv",
                [
                    "p25",
                    "p50",
                    "p75",
                    "p95",
                    "p99",
                    "p999",
                    "high_visit_threshold",
                ],
                [[2, 4, 6, 8, 9, 10, 10]],
            )

            parquet_path = root / "clean.parquet"
            escaped_path = str(parquet_path).replace("'", "''")
            connection = duckdb.connect()
            try:
                connection.execute(
                    f"COPY (SELECT range::BIGINT AS daily_visits FROM range(12)) "
                    f"TO '{escaped_path}' (FORMAT PARQUET)"
                )
            finally:
                connection.close()

            result = run(
                parse_args(
                    [
                        "--summary-dir",
                        str(summaries),
                        "--clean-data",
                        str(parquet_path),
                        "--output-root",
                        str(reports),
                        "--top-brands",
                        "3",
                        "--top-categories",
                        "3",
                    ]
                )
            )

            static_paths = [Path(path) for path in result["static_plots"]]
            interactive_paths = [Path(path) for path in result["interactive_plots"]]
            notes_path = Path(result["interpretation_notes"])
            for path in static_paths:
                self.assertGreater(path.stat().st_size, 10_000)
                with Image.open(path) as image:
                    self.assertGreaterEqual(image.width, 1_000)
                    self.assertGreaterEqual(image.height, 600)
            for path in interactive_paths:
                self.assertGreater(path.stat().st_size, 1_000_000)

            monthly_html = interactive_paths[0].read_text(encoding="utf-8")
            market_html = interactive_paths[1].read_text(encoding="utf-8")
            notes = notes_path.read_text(encoding="utf-8")

        self.assertIn("Plotly.newPlot", monthly_html)
        self.assertIn("Mean daily visits", monthly_html)
        self.assertIn("rangeslider", monthly_html)
        self.assertEqual(monthly_html.count('"yaxis.title.text"'), 2)
        self.assertIn(
            '"yaxis.title.text":"Mean visits per store-day record"', monthly_html
        )
        self.assertIn(
            '"yaxis.title.text":"Total transformed visits (billions)"', monthly_html
        )
        self.assertIn("Plotly.newPlot", market_html)
        self.assertIn("Market A", market_html)
        self.assertIn("Bubble area represents", market_html)
        self.assertIn("## Static plots", notes)
        self.assertIn("## Interactive plots", notes)
        self.assertEqual(
            sum(item["count"] for item in result["distribution_bins"]), 12
        )


if __name__ == "__main__":
    unittest.main()
