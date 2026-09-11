"""Validation for compact, app-ready FinalFlow dashboard context exports."""

from __future__ import annotations

import csv
import json
import tempfile
import unittest
from pathlib import Path

from paddydash.services.mobility_config import default_mobility_config
from scripts.data.build_finalflow_dashboard_context import (
    OUTPUT_FIELDS,
    PRIMARY_KEYS,
    parse_args,
    run,
)


class DashboardContextExportTests(unittest.TestCase):
    """Ensure the support layer remains compact, canonical, and provenance-safe."""

    def build(self, output_dir: Path, overwrite: bool = False) -> None:
        args = ["--output-dir", str(output_dir)]
        if overwrite:
            args.append("--overwrite")
        run(parse_args(args))

    def test_context_exports_have_expected_schema_and_provenance(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            output = Path(temp_dir)
            self.build(output)
            for filename, fields in OUTPUT_FIELDS.items():
                with (output / filename).open(newline="", encoding="utf-8") as stream:
                    rows = list(csv.DictReader(stream))
                self.assertTrue(rows)
                self.assertEqual(list(rows[0]), fields)
                self.assertTrue(all(row["data_type"] in {"provided", "derived", "synthetic", "web"} for row in rows))
                keys = [tuple(row[field] for field in PRIMARY_KEYS[filename]) for row in rows]
                self.assertEqual(len(keys), len(set(keys)))
            config = default_mobility_config()
            with (output / "match_timeline_summary.csv").open(newline="", encoding="utf-8") as stream:
                timeline = list(csv.DictReader(stream))
            self.assertEqual({row["phase_id"] for row in timeline}, {phase.phase_id.value for phase in config.phases})
            self.assertEqual([int(row["time_minutes"]) for row in timeline], sorted(int(row["time_minutes"]) for row in timeline))
            with (output / "scenario_comparison.csv").open(newline="", encoding="utf-8") as stream:
                scenarios = list(csv.DictReader(stream))
            self.assertEqual({row["scenario_id"] for row in scenarios}, {scenario.scenario_id.value for scenario in config.scenarios})
            self.assertTrue(all(int(row["peak_queue_passengers"]) >= 0 for row in scenarios))

    def test_ai_context_is_compact_and_has_explicit_limitations(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            output = Path(temp_dir)
            self.build(output)
            context = json.loads((output / "finalflow_ai_context.json").read_text(encoding="utf-8"))
            self.assertEqual(len(context["corridor_nodes"]), 5)
            self.assertEqual(len(context["access_zones"]), 5)
            self.assertEqual(len(context["scenario_summaries"]), 5)
            self.assertEqual(context["provenance"]["data_type"], "derived")
            self.assertTrue(context["limitations"])
            self.assertNotIn("placekey", json.dumps(context))

    def test_regeneration_is_deterministic_and_requires_overwrite(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            output = Path(temp_dir)
            self.build(output)
            before = {path.name: path.read_bytes() for path in output.iterdir()}
            with self.assertRaisesRegex(FileExistsError, "Refusing to overwrite"):
                self.build(output)
            self.build(output, overwrite=True)
            after = {path.name: path.read_bytes() for path in output.iterdir()}
            self.assertEqual(before, after)


if __name__ == "__main__":
    unittest.main()
