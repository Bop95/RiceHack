"""Tests for the reproducible synthetic store-visit scenario generator."""

from __future__ import annotations

import csv
import tempfile
import unittest
from collections import defaultdict
from datetime import datetime
from pathlib import Path

from scripts.synthetic.generate_store_visit_scenarios import (
    DISCLAIMER,
    FIELDNAMES,
    SCENARIOS,
    parse_args,
    run,
)


def write_summary(path: Path, label: str) -> None:
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.writer(stream)
        writer.writerow([label, "total_visits", "mean_daily_visits", "data_type"])
        writer.writerow([f"{label.title()} A", 1_000_000, 500, "derived"])
        writer.writerow([f"{label.title()} B", 500_000, 250, "derived"])


def write_brand_category_summary(path: Path) -> None:
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.writer(stream)
        writer.writerow(
            [
                "brand",
                "category",
                "record_count",
                "total_visits",
                "mean_daily_visits",
                "data_type",
            ]
        )
        writer.writerow(["Brand A", "Category A", 100, 1_000_000, 500, "derived"])
        writer.writerow(["Brand B", "Category B", 80, 500_000, 250, "derived"])


class StoreVisitScenarioTests(unittest.TestCase):
    def test_generation_is_reproducible_and_clearly_labeled(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            brands = root / "brands.csv"
            brand_categories = root / "brand_categories.csv"
            output = root / "scenarios.csv"
            dictionary = root / "dictionary.md"
            write_summary(brands, "brand")
            write_brand_category_summary(brand_categories)
            args = parse_args(
                [
                    "--brand-summary",
                    str(brands),
                    "--brand-category-summary",
                    str(brand_categories),
                    "--output",
                    str(output),
                    "--dictionary",
                    str(dictionary),
                    "--rows",
                    "5000",
                    "--seed",
                    "2026",
                ]
            )
            result = run(args)
            first_bytes = output.read_bytes()
            with output.open(encoding="utf-8") as stream:
                rows = list(csv.DictReader(stream))
            run(parse_args([*self.args_with_overwrite(args)]))
            regenerated_bytes = output.read_bytes()
            dictionary_text = dictionary.read_text(encoding="utf-8")

        self.assertEqual(result["rows"], 5000)
        self.assertEqual(set(rows[0]), set(FIELDNAMES))
        self.assertEqual({row["scenario_id"] for row in rows}, set(SCENARIOS))
        self.assertTrue(all(row["data_type"] == "synthetic" for row in rows))
        self.assertTrue(all(row["is_synthetic"] == "true" for row in rows))
        self.assertTrue(all(int(row["baseline_visits"]) >= 0 for row in rows))
        self.assertTrue(all(int(row["estimated_visits"]) >= 0 for row in rows))
        valid_pairs = {("Brand A", "Category A"), ("Brand B", "Category B")}
        self.assertTrue(all((row["brand"], row["category"]) in valid_pairs for row in rows))
        totals = defaultdict(lambda: [0, 0])
        for row in rows:
            totals[row["scenario_id"]][0] += int(row["baseline_visits"])
            totals[row["scenario_id"]][1] += int(row["estimated_visits"])
        for scenario_id, (baseline, estimated) in totals.items():
            realized = estimated / baseline
            self.assertAlmostEqual(
                realized, SCENARIOS[scenario_id]["multiplier"], delta=0.03
            )
        self.assertTrue(
            all(
                datetime.fromisoformat(row["timestamp"]) < datetime(2026, 6, 1)
                for row in rows
            )
        )
        self.assertEqual(first_bytes, regenerated_bytes)
        self.assertIn(DISCLAIMER, dictionary_text)

    @staticmethod
    def args_with_overwrite(args: object) -> list[str]:
        return [
            "--brand-summary",
            str(args.brand_summary),
            "--brand-category-summary",
            str(args.brand_category_summary),
            "--output",
            str(args.output),
            "--dictionary",
            str(args.dictionary),
            "--rows",
            str(args.rows),
            "--seed",
            str(args.seed),
            "--overwrite",
        ]

    def test_row_limit_guard(self) -> None:
        with self.assertRaisesRegex(ValueError, "between 5,000 and 20,000"):
            from scripts.synthetic.generate_store_visit_scenarios import generate_rows

            generate_rows(100, 1, [], {})


if __name__ == "__main__":
    unittest.main()
