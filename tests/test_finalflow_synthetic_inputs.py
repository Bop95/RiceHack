"""Tests for deterministic synthetic mobility/access input generation."""

from __future__ import annotations

import csv
import json
import tempfile
import unittest
from copy import deepcopy
from pathlib import Path

from scripts.synthetic.generate_finalflow_synthetic_inputs import (
    FIELDS,
    SEED,
    generate_capacity,
    generate_first_last_mile,
    generate_parking,
    generate_passenger_demand,
    generate_pedestrians,
    generate_road_access,
    emissions_factors,
    interventions,
    parse_args,
    run,
    validate,
)
from paddydash.services.mobility_config import default_mobility_config


class FinalFlowSyntheticInputTests(unittest.TestCase):
    def test_generation_schema_provenance_and_determinism(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            output = Path(temp_dir) / "inputs"
            first = run(parse_args(["--output-dir", str(output)]))
            bytes_before = {name: (output / name).read_bytes() for name in FIELDS}
            manifest_before = (output / "manifest.json").read_bytes()
            second = run(parse_args(["--output-dir", str(output), "--overwrite"]))
            self.assertEqual(first["row_counts"], second["row_counts"])
            self.assertEqual(bytes_before, {name: (output / name).read_bytes() for name in FIELDS})
            self.assertEqual(manifest_before, (output / "manifest.json").read_bytes())
            manifest = json.loads((output / "manifest.json").read_text())
            self.assertEqual(manifest["random_seed"], SEED)
            self.assertEqual(manifest["config_id"], "finalflow_corridor_v1")
            self.assertEqual(manifest["row_counts"]["matchday_passenger_demand.csv"], 16_000)
            for name, columns in FIELDS.items():
                with (output / name).open(newline="") as stream:
                    rows = list(csv.DictReader(stream))
                self.assertEqual(set(rows[0]), set(columns))
                self.assertTrue(all(row["data_type"] == "synthetic" for row in rows))
                self.assertTrue(all(row["confidence_type"] == "scenario" for row in rows))

    def test_input_relationships_are_validated(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            output = Path(temp_dir) / "inputs"
            run(parse_args(["--output-dir", str(output)]))
            with (output / "matchday_passenger_demand.csv").open(newline="") as stream:
                demand = list(csv.DictReader(stream))
            grouped = {}
            for row in demand:
                access_node = row["origin_node"] if row["direction"] == "inbound" else row["destination_node"]
                key = row["scenario_id"], row["time_minutes"], row["direction"], access_node
                grouped[key] = grouped.get(key, 0.0) + float(row["mode_share"])
                self.assertGreaterEqual(int(row["passenger_demand"]), 0)
                self.assertEqual(int(row["time_minutes"]) % 5, 0)
            self.assertTrue(all(abs(value - 1.0) < 1e-9 for value in grouped.values()))
            for scenario_id in {row["scenario_id"] for row in demand}:
                for direction in ("inbound", "outbound"):
                    total = sum(int(row["passenger_demand"]) for row in demand if row["scenario_id"] == scenario_id and row["direction"] == direction)
                    self.assertEqual(total, 6_000)
            with (output / "transit_service_capacity.csv").open(newline="") as stream:
                for row in csv.DictReader(stream):
                    self.assertGreaterEqual(int(row["effective_capacity"]), 0)
                    self.assertEqual(int(row["effective_capacity"]), int(int(row["scheduled_capacity"]) * float(row["disruption_factor"]) * float(row["weather_factor"])))
            with (output / "parking_demand.csv").open(newline="") as stream:
                parking = list(csv.DictReader(stream))
            self.assertTrue(all(0 <= int(row["occupied_spaces_input"]) <= int(row["estimated_spaces"]) for row in parking))

    def test_scenario_assumptions_change_only_documented_inputs(self) -> None:
        config = default_mobility_config()
        demand = generate_passenger_demand(config)
        capacity = generate_capacity(config)
        def demand_key(row):
            return (
                row["time_minutes"], row["origin_node"], row["destination_node"],
                row["mode"], row["direction"],
            )
        baseline = {demand_key(row): row for row in demand if row["scenario_id"] == "baseline"}
        disruption = {demand_key(row): row for row in demand if row["scenario_id"] == "rail_disruption"}
        self.assertEqual(
            [row["passenger_demand"] for row in baseline.values()],
            [row["passenger_demand"] for row in disruption.values()],
        )
        rain = [row for row in demand if row["scenario_id"] == "rain" and row["time_minutes"] == -30 and row["direction"] == "inbound"]
        self.assertAlmostEqual(sum(float(row["mode_share"]) for row in rain), 4.0)
        self.assertLess(next(float(row["mode_share"]) for row in rain if row["mode"] == "walk"), 0.15)
        rail_disruption = [row for row in capacity if row["scenario_id"] == "rail_disruption" and row["mode"] == "rail"]
        self.assertTrue(all(float(row["disruption_factor"]) == 0.5 for row in rail_disruption))
        rain_walk = [row for row in capacity if row["scenario_id"] == "rain" and row["mode"] == "walk"]
        self.assertTrue(all(float(row["weather_factor"]) == 0.8 for row in rain_walk))

    def test_validator_rejects_invalid_capacity_and_unknown_phase(self) -> None:
        config = default_mobility_config()
        demand = generate_passenger_demand(config)
        road = generate_road_access(config, demand)
        datasets = {
            "matchday_passenger_demand.csv": demand,
            "transit_service_capacity.csv": generate_capacity(config),
            "first_last_mile_demand.csv": generate_first_last_mile(config, demand),
            "road_access_demand.csv": road,
            "parking_demand.csv": generate_parking(config, road),
            "pedestrian_demand.csv": generate_pedestrians(config, demand),
            "interventions.csv": interventions(),
            "emissions_factors.csv": emissions_factors(),
        }
        datasets["transit_service_capacity.csv"][0] = deepcopy(datasets["transit_service_capacity.csv"][0])
        datasets["transit_service_capacity.csv"][0]["effective_capacity"] = 1
        with self.assertRaisesRegex(ValueError, "Capacity factors"):
            validate(datasets, config)
        datasets["transit_service_capacity.csv"][0]["effective_capacity"] = datasets["transit_service_capacity.csv"][0]["scheduled_capacity"]
        datasets["matchday_passenger_demand.csv"][0] = deepcopy(datasets["matchday_passenger_demand.csv"][0])
        datasets["matchday_passenger_demand.csv"][0]["phase_id"] = "unknown_phase"
        with self.assertRaisesRegex(ValueError, "unknown scenario or phase"):
            validate(datasets, config)

    def test_invalid_seed_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            with self.assertRaisesRegex(ValueError, "fixed seed"):
                run(parse_args(["--output-dir", temp_dir, "--seed", "7"]))


if __name__ == "__main__":
    unittest.main()
