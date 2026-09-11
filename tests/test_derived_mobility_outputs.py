"""Contract tests for deterministic mobility outputs derived from synthetic inputs."""

from __future__ import annotations

import csv
import json
import tempfile
import unittest
from datetime import datetime
from pathlib import Path

from scripts.synthetic.derive_finalflow_mobility_outputs import (
    OUTPUT_FIELDS,
    parse_args as parse_derive_args,
    profile_runs,
    read_inputs,
    run as derive_run,
    validate_profile_run,
)
from scripts.synthetic.generate_finalflow_synthetic_inputs import (
    parse_args as parse_input_args,
    run as generate_inputs,
)
from paddydash.services.mobility_config import default_mobility_config


class DerivedMobilityOutputTests(unittest.TestCase):
    """Verify the derived layer does not fabricate results or lose passengers."""

    def build_outputs(self, root: Path) -> tuple[Path, Path]:
        inputs = root / "synthetic"
        exports = root / "exports"
        generate_inputs(parse_input_args(["--output-dir", str(inputs)]))
        derive_run(parse_derive_args([
            "--input-dir", str(inputs), "--output-dir", str(exports),
        ]))
        return inputs, exports

    def test_output_schema_provenance_and_manifest(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            _, exports = self.build_outputs(Path(temp_dir))
            expected_rows = {
                "mobility_node_timeseries.csv": 2_500,
                "mobility_edge_timeseries.csv": 4_000,
                "scenario_summary.csv": 5,
                "mobility_access_summary.csv": 5,
                "intervention_comparison.csv": 13,
            }
            for filename, row_count in expected_rows.items():
                with (exports / filename).open(newline="", encoding="utf-8") as stream:
                    rows = list(csv.DictReader(stream))
                self.assertEqual(len(rows), row_count)
                self.assertEqual(list(rows[0]), OUTPUT_FIELDS[filename])
                self.assertTrue(all(row["data_type"] == "derived" for row in rows))
                self.assertTrue(all(row["assumption_note"] for row in rows))
            phases = {phase.phase_id.value for phase in default_mobility_config().phases}
            with (exports / "mobility_node_timeseries.csv").open(newline="", encoding="utf-8") as stream:
                node_timeseries = list(csv.DictReader(stream))
            self.assertTrue(all(row["phase_id"] in phases for row in node_timeseries))
            self.assertTrue(all(int(row["time_minutes"]) % 5 == 0 for row in node_timeseries))
            self.assertTrue(all(datetime.fromisoformat(row["timestamp"].replace("Z", "+00:00")) for row in node_timeseries))
            self.assertTrue(all(int(row["queue_passengers"]) >= 0 for row in node_timeseries))
            with (exports / "mobility_edge_timeseries.csv").open(newline="", encoding="utf-8") as stream:
                edge_timeseries = list(csv.DictReader(stream))
            self.assertTrue(all(int(row["capacity"]) >= 0 for row in edge_timeseries))
            self.assertTrue(all(int(row["throughput"]) <= int(row["capacity"]) for row in edge_timeseries))
            manifest = json.loads((exports / "mobility_manifest.json").read_text())
            self.assertEqual(manifest["provenance"]["data_type"], "derived")
            self.assertEqual(manifest["provenance"]["input_data_type"], "synthetic")
            self.assertEqual(manifest["emissions"]["status"], "not_derived_missing_mode_distance_inputs")

    def test_replay_conserves_passengers_and_respects_capacity(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            inputs, _ = self.build_outputs(Path(temp_dir))
            runs = profile_runs(read_inputs(inputs))
            for scenario_id, profile in runs.items():
                with self.subTest(scenario=scenario_id):
                    validate_profile_run(profile)
                    self.assertTrue(profile.completed)
                    self.assertEqual(profile.total_arrivals, 6_000)
                    self.assertEqual(profile.total_departures, 6_000)
                    for snapshot in profile.snapshots:
                        self.assertEqual(
                            snapshot.total_entered,
                            snapshot.total_people_in_system + snapshot.total_exited,
                        )
                        for edge in snapshot.edge_states:
                            self.assertLessEqual(edge.throughput, edge.capacity)
                            self.assertLessEqual(edge.throughput, edge.demand)

    def test_scenario_effects_are_calculated_from_profiles(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            _, exports = self.build_outputs(Path(temp_dir))
            with (exports / "scenario_summary.csv").open(newline="", encoding="utf-8") as stream:
                summaries = {row["scenario_id"]: row for row in csv.DictReader(stream)}
            baseline = summaries["baseline"]
            disruption = summaries["rail_disruption"]
            boost = summaries["rail_capacity_boost"]
            rain = summaries["rain"]
            staggered = summaries["staggered_departure"]
            self.assertGreater(
                int(disruption["passenger_delay_proxy_person_minutes"]),
                int(baseline["passenger_delay_proxy_person_minutes"]),
            )
            self.assertLess(
                int(boost["passenger_delay_proxy_person_minutes"]),
                int(baseline["passenger_delay_proxy_person_minutes"]),
            )
            self.assertLess(
                int(staggered["peak_post_final_whistle_queue_passengers"]),
                int(baseline["peak_post_final_whistle_queue_passengers"]),
            )
            self.assertGreater(
                int(rain["total_clearance_minutes"]),
                int(baseline["total_clearance_minutes"]),
            )

    def test_regeneration_is_deterministic_and_output_overwrite_is_explicit(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            inputs, exports = self.build_outputs(Path(temp_dir))
            before = {
                path.name: path.read_bytes()
                for path in exports.iterdir() if path.is_file() and path.name != ".gitkeep"
            }
            with self.assertRaisesRegex(FileExistsError, "Refusing to overwrite"):
                derive_run(parse_derive_args([
                    "--input-dir", str(inputs), "--output-dir", str(exports),
                ]))
            derive_run(parse_derive_args([
                "--input-dir", str(inputs), "--output-dir", str(exports), "--overwrite",
            ]))
            after = {
                path.name: path.read_bytes()
                for path in exports.iterdir() if path.is_file() and path.name != ".gitkeep"
            }
            self.assertEqual(before, after)


if __name__ == "__main__":
    unittest.main()
