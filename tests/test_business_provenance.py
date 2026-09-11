"""Check synthetic labels through the business scenario and export pipeline."""

import contextlib
import importlib.util
import io
import tempfile
import unittest
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]


def load_script(name: str):
    spec = importlib.util.spec_from_file_location(
        'business_' + name, ROOT / 'notebooks/duc-anh/src' / (name + '.py')
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


generator = load_script('generate_scenarios')
exporter = load_script('export_powerbi')


class BusinessProvenanceTests(unittest.TestCase):
    def assert_provenance(self, frame: pd.DataFrame) -> None:
        self.assertEqual(set(frame['data_type']), {'synthetic'})
        self.assertEqual(set(frame['data_confidence']), {'scenario'})
        self.assertTrue(frame['scenario_id'].fillna('').str.strip().ne('').all())
        self.assertTrue(frame['assumption_note'].str.contains('not observed evidence').all())

    def test_generation_and_export_preserve_provenance_and_values(self) -> None:
        with tempfile.TemporaryDirectory() as directory, contextlib.redirect_stdout(io.StringIO()):
            root = Path(directory)
            generator.score_scenarios(root)
            scenarios = pd.read_csv(root / 'vendor_zone_scenarios.csv')
            self.assertEqual(len(scenarios), 50)
            self.assert_provenance(scenarios)
            exporter.export_integration_schema(root)
            exported = pd.read_csv(root / 'finalflow_business_integration.csv')
            self.assert_provenance(exported)
            pd.testing.assert_frame_equal(exported[scenarios.columns], scenarios)
            self.assertTrue(exported['reason'].str.startswith('Synthetic scenario:').all())

    def test_legacy_high_confidence_rows_are_reclassified(self) -> None:
        with tempfile.TemporaryDirectory() as directory, contextlib.redirect_stdout(io.StringIO()):
            root = Path(directory)
            legacy = pd.DataFrame({
                'zone_id': ['ZONE_001', 'ZONE_002', 'ZONE_003'],
                'placement_class': ['Recommended', 'Controlled', 'Avoided'],
                'data_confidence': ['High'] * 3,
                'data_type': ['provided'] * 3,
            })
            legacy.to_csv(root / 'vendor_zone_scenarios.csv', index=False)
            exporter.export_integration_schema(root)
            exported = pd.read_csv(root / 'finalflow_business_integration.csv')
            self.assert_provenance(exported)
            self.assertEqual(list(exported['zone_id']), list(legacy['zone_id']))
            self.assertTrue(exported['reason'].str.startswith('Synthetic scenario:').all())

    def test_existing_scenario_ids_survive_and_blank_ids_are_filled(self) -> None:
        with tempfile.TemporaryDirectory() as directory, contextlib.redirect_stdout(io.StringIO()):
            root = Path(directory)
            pd.DataFrame({
                'zone_id': ['ZONE_001', 'ZONE_002'],
                'placement_class': ['Recommended', 'Avoided'],
                'scenario_id': ['custom_scenario', ' '],
            }).to_csv(root / 'vendor_zone_scenarios.csv', index=False)
            exporter.export_integration_schema(root)
            exported = pd.read_csv(root / 'finalflow_business_integration.csv')
            self.assert_provenance(exported)
            self.assertEqual(exported.iloc[0]['scenario_id'], 'custom_scenario')

    def test_tracked_business_tables_are_labeled_synthetic(self) -> None:
        for name in ('vendor_zone_scenarios.csv', 'finalflow_business_integration.csv'):
            with self.subTest(name=name):
                self.assert_provenance(pd.read_csv(ROOT / 'notebooks/duc-anh/data_clean' / name))


if __name__ == '__main__':
    unittest.main()
