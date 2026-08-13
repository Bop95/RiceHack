"""Focused fixture tests for the spatial and weather integration builders."""

from __future__ import annotations

import csv
import subprocess
import sys
import tempfile
import unittest
from itertools import product
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
from zipfile import ZIP_DEFLATED, ZipFile

from scripts.data.build_spatial_heat_locations import (
    assign_terciles,
    build as build_spatial,
    grid_key,
    nearest_uhi,
    output_fields as spatial_output_fields,
    parse_args as parse_spatial_args,
    write_csv as write_spatial_csv,
)
from scripts.data.build_weather_chat_summaries import (
    build as build_weather,
    parse_args as parse_weather_args,
    risk_flags,
    risk_level,
    write_csv as write_weather_csv,
)


def write_zip_csv(
    archive: ZipFile,
    member: str,
    fieldnames: list[str],
    rows: list[dict[str, object]],
) -> None:
    import io

    buffer = io.StringIO(newline="")
    writer = csv.DictWriter(buffer, fieldnames=fieldnames)
    writer.writeheader()
    writer.writerows(rows)
    archive.writestr(member, buffer.getvalue())


class SpatialWeatherBuilderTests(unittest.TestCase):
    def test_deployment_csv_bytes_use_lf_on_every_platform(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            spatial_path = root / "spatial.csv"
            weather_path = root / "weather.csv"
            spatial_row = {field: "fixture" for field in spatial_output_fields()}
            write_spatial_csv(spatial_path, [spatial_row])
            write_weather_csv(weather_path, [{"metric_id": "fixture", "value": 1}])

            for path in (spatial_path, weather_path):
                with self.subTest(path=path.name):
                    payload = path.read_bytes()
                    self.assertIn(b"\n", payload)
                    self.assertNotIn(b"\r\n", payload)

    def test_metadata_defaults_beside_redirected_output(self) -> None:
        cases = (
            (
                parse_spatial_args,
                [
                    "builder",
                    "--poi-uhi-zip",
                    "poi.zip",
                    "--spending-zip",
                    "spending.zip",
                    "--output",
                    "temporary/spatial.csv",
                    "--generated-at",
                    "2026-08-12T00:00:00Z",
                ],
                Path("temporary/spatial.metadata.json"),
            ),
            (
                parse_weather_args,
                [
                    "builder",
                    "--input",
                    "weather.csv",
                    "--output",
                    "temporary/weather.csv",
                    "--generated-at",
                    "2026-08-12T00:00:00Z",
                ],
                Path("temporary/weather.metadata.json"),
            ),
        )
        for parser, arguments, expected in cases:
            with self.subTest(parser=parser.__module__):
                with patch.object(sys, "argv", arguments):
                    self.assertEqual(parser().metadata, expected)

    def test_spatial_builder_rejects_invalid_bounds_before_reading_sources(self) -> None:
        base = {
            "poi_uhi_zip": Path("missing-poi.zip"),
            "spending_zip": Path("missing-spending.zip"),
            "output": Path("unused.csv"),
            "generated_at": "2026-08-12T00:00:00Z",
            "source_commit": "fixture",
            "min_lat": 40.4,
            "max_lat": 41.1,
            "min_lon": -74.5,
            "max_lon": -73.5,
            "max_uhi_distance_m": 250.0,
        }
        for changes in (
            {"min_lat": 41.1, "max_lat": 40.4},
            {"min_lon": -73.5, "max_lon": -74.5},
            {"max_uhi_distance_m": 0.0},
            {"max_uhi_distance_m": float("nan")},
        ):
            with self.subTest(changes=changes):
                with self.assertRaises(ValueError):
                    build_spatial(SimpleNamespace(**(base | changes)))

    def test_rank_terciles_are_deterministic(self) -> None:
        tiers = assign_terciles({"c": 30.0, "a": 10.0, "b": 20.0})
        self.assertEqual(tiers, {"a": "Low", "b": "Medium", "c": "High"})
        tied = assign_terciles({"b": 10.0, "a": 10.0, "c": 20.0})
        self.assertEqual(tied, {"a": "Low", "b": "Medium", "c": "High"})

    def test_nearest_uhi_respects_distance_limit_and_missing_evidence(self) -> None:
        latitude, longitude = 40.75, -74.0
        grid = {
            grid_key(latitude, longitude): [
                (latitude, longitude + 0.002, 8.0),
            ]
        }
        matched, distance = nearest_uhi(latitude, longitude, grid, 250.0)
        self.assertEqual(matched, 8.0)
        self.assertIsNotNone(distance)
        self.assertLess(distance or 0, 250.0)
        self.assertEqual(nearest_uhi(latitude, longitude, grid, 100.0), (None, None))

    def test_builder_help_is_safe_in_a_legacy_windows_code_page(self) -> None:
        scripts = (
            "scripts/data/build_spatial_heat_locations.py",
            "scripts/data/build_weather_chat_summaries.py",
        )
        for script in scripts:
            with self.subTest(script=script):
                completed = subprocess.run(
                    [sys.executable, script, "--help"],
                    check=False,
                    capture_output=True,
                    encoding="cp1252",
                    errors="strict",
                    text=True,
                )
                self.assertEqual(completed.returncode, 0, completed.stderr)
                self.assertIn("usage:", completed.stdout)

    def test_spatial_builder_excludes_synthetic_and_unknown_rows(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            poi_zip = root / "poi_uhi_summary.zip"
            spending_zip = root / "spending_summary.zip"
            poi_fields = [
                "PLACEKEY",
                "LOCATION_NAME",
                "TOP_CATEGORY",
                "LATITUDE",
                "LONGITUDE",
                "CITY",
                "REGION",
                "INCLUDES_PARKING_LOT",
                "IS_SYNTHETIC",
            ]
            with ZipFile(poi_zip, "w", ZIP_DEFLATED) as archive:
                write_zip_csv(
                    archive,
                    "poi_summary.csv",
                    poi_fields,
                    [
                        {
                            "PLACEKEY": "valid",
                            "LOCATION_NAME": "Valid <Location>",
                            "TOP_CATEGORY": "Food",
                            "LATITUDE": 40.75,
                            "LONGITUDE": -74.0,
                            "CITY": "New York",
                            "REGION": "NY",
                            "INCLUDES_PARKING_LOT": "False",
                            "IS_SYNTHETIC": "False",
                        },
                        {
                            "PLACEKEY": "synthetic",
                            "LOCATION_NAME": "Synthetic",
                            "TOP_CATEGORY": "Food",
                            "LATITUDE": 40.75,
                            "LONGITUDE": -74.0,
                            "CITY": "New York",
                            "REGION": "NY",
                            "INCLUDES_PARKING_LOT": "False",
                            "IS_SYNTHETIC": "True",
                        },
                        {
                            "PLACEKEY": "unknown",
                            "LOCATION_NAME": "Unknown",
                            "TOP_CATEGORY": "Food",
                            "LATITUDE": 40.75,
                            "LONGITUDE": -74.0,
                            "CITY": "New York",
                            "REGION": "NY",
                            "INCLUDES_PARKING_LOT": "",
                            "IS_SYNTHETIC": "",
                        },
                    ],
                )
                write_zip_csv(
                    archive,
                    "uhi_summary.csv",
                    ["LATITUDE", "LONGITUDE", "UHI"],
                    [{"LATITUDE": 40.75, "LONGITUDE": -74.0, "UHI": 9}],
                )
            with ZipFile(spending_zip, "w", ZIP_DEFLATED) as archive:
                write_zip_csv(
                    archive,
                    "spending_summary.csv",
                    ["PLACEKEY", "RAW_TOTAL_SPEND", "RAW_NUM_CUSTOMERS"],
                    [
                        {"PLACEKEY": "valid", "RAW_TOTAL_SPEND": 100, "RAW_NUM_CUSTOMERS": 2},
                        {"PLACEKEY": "valid", "RAW_TOTAL_SPEND": 200, "RAW_NUM_CUSTOMERS": 3},
                        {"PLACEKEY": "valid", "RAW_TOTAL_SPEND": -50, "RAW_NUM_CUSTOMERS": 1},
                    ],
                )
            args = SimpleNamespace(
                poi_uhi_zip=poi_zip,
                spending_zip=spending_zip,
                output=root / "spatial.csv",
                generated_at="2026-08-12T00:00:00Z",
                source_commit="fixture",
                min_lat=40.4,
                max_lat=41.1,
                min_lon=-74.5,
                max_lon=-73.5,
                max_uhi_distance_m=250.0,
            )
            rows, metadata = build_spatial(args)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["placekey"], "valid")
        self.assertEqual(rows[0]["heat_concern"], "High")
        self.assertNotIn("total_spend", rows[0])
        self.assertEqual(metadata["input_counts"]["accepted_spending_rows"], 2)
        self.assertEqual(metadata["input_counts"]["rejected_invalid_spending_rows"], 1)
        self.assertEqual(metadata["rejected_by_reason"]["rejected_synthetic"], 1)
        self.assertEqual(
            metadata["rejected_by_reason"]["rejected_unknown_synthetic_status"], 1
        )

    def test_weather_builder_rejects_invalid_temperature_order(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source = root / "daily_weather_clean.csv"
            fields = [
                "location_id",
                "date",
                "temperature_min_c",
                "temperature_avg_c",
                "temperature_max_c",
                "precipitation_raw",
                "precipitation_mm",
                "wind_speed_knots",
                "visibility_km",
            ]
            with source.open("w", encoding="utf-8", newline="") as stream:
                writer = csv.DictWriter(stream, fieldnames=fields)
                writer.writeheader()
                writer.writerows(
                    [
                        {
                            "location_id": "A",
                            "date": "2024-06-01",
                            "temperature_min_c": 20,
                            "temperature_avg_c": 25,
                            "temperature_max_c": 31,
                            "precipitation_raw": -1,
                            "precipitation_mm": 0,
                            "wind_speed_knots": 5,
                            "visibility_km": 10,
                        },
                        {
                            "location_id": "A",
                            "date": "2024-06-01",
                            "temperature_min_c": 20,
                            "temperature_avg_c": 25,
                            "temperature_max_c": 31,
                            "precipitation_raw": -1,
                            "precipitation_mm": 0,
                            "wind_speed_knots": 5,
                            "visibility_km": 10,
                        },
                        {
                            "location_id": "C",
                            "date": "2024-06-03",
                            "temperature_min_c": 20,
                            "temperature_avg_c": 25,
                            "temperature_max_c": 30,
                            "precipitation_raw": 100,
                            "precipitation_mm": 2,
                            "wind_speed_knots": 5,
                            "visibility_km": 10,
                        },
                        {
                            "location_id": "B",
                            "date": "2024-06-02",
                            "temperature_min_c": 20,
                            "temperature_avg_c": 35,
                            "temperature_max_c": 30,
                            "precipitation_raw": 100,
                            "precipitation_mm": 1,
                            "wind_speed_knots": 5,
                            "visibility_km": 10,
                        },
                    ]
                )
            args = SimpleNamespace(
                input=source,
                output=root / "weather.csv",
                generated_at="2026-08-12T00:00:00Z",
                source_commit="fixture",
            )
            rows, metadata = build_weather(args)
        hot = next(row for row in rows if row["metric_id"] == "summer_hot_observation_share")
        self.assertEqual(hot["numerator"], 1)
        self.assertEqual(hot["denominator"], 1)
        self.assertEqual(metadata["rejected_observation_rows"], 3)
        self.assertEqual(
            metadata["rejected_by_reason"],
            {
                "invalid_temperature_order": 1,
                "duplicate_station_date": 1,
                "invalid_precipitation_conversion": 1,
            },
        )

    def test_weather_threshold_boundaries_and_all_flag_combinations(self) -> None:
        boundary_row = {
            "temperature_max_c": "30",
            "precipitation_mm": "0",
            "wind_speed_knots": "20",
            "visibility_km": "5",
        }
        self.assertEqual(risk_flags(boundary_row), (True, False, True, True))
        boundary_row["precipitation_mm"] = "0.01"
        self.assertEqual(risk_flags(boundary_row), (True, True, True, True))

        weights = (0.35, 0.30, 0.15, 0.20)
        for flags in product((False, True), repeat=4):
            with self.subTest(flags=flags):
                score = sum(weight for enabled, weight in zip(flags, weights) if enabled)
                expected = "High" if score >= 0.6 else "Medium" if score >= 0.3 else "Low"
                self.assertEqual(risk_level(flags), expected)


if __name__ == "__main__":
    unittest.main()
