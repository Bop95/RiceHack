"""Prepared-data correctness, missing evidence and all analytical page selections."""

import csv
import json
import os
from pathlib import Path
import unittest
from unittest.mock import patch

from streamlit.testing.v1 import AppTest

from paddydash.services.finalflow_data import (
    current_mobility, evaluate_rules, load_table, percent_change, phase_window, validate_rows,
)
from paddydash.services.mobility_config import default_mobility_config


ROOT = Path(__file__).resolve().parents[1]
PAGES = (
    ('overview', 'render_overview'), ('matchday_timeline', 'render_matchday_timeline'),
    ('mobility', 'render_mobility'), ('project_evidence', 'render_project_evidence'),
    ('weather_heat', 'render_weather_heat'), ('scenario_explorer', 'render_scenario_explorer'),
)


def raw_rows(name):
    with (ROOT / 'data/exports' / name).open() as stream:
        return list(csv.DictReader(stream))


class PreparedMetricTests(unittest.TestCase):
    def test_current_aggregates_match_csv_independently(self):
        nodes = raw_rows('mobility_node_timeseries.csv')
        edges = raw_rows('mobility_edge_timeseries.csv')
        for scenario in ('baseline', 'rain', 'rail_disruption', 'rail_capacity_boost', 'staggered_departure'):
            for minute in (-135, 0, 135, 165, 315):
                with self.subTest(scenario=scenario, minute=minute):
                    context = current_mobility(scenario, minute)
                    selected = [r for r in nodes if r['scenario_id'] == scenario and int(r['time_minutes']) == minute]
                    selected_edges = [r for r in edges if r['scenario_id'] == scenario and int(r['time_minutes']) == minute]
                    self.assertTrue(context['available'])
                    self.assertEqual(context['pressure'], sum(int(r['queue_passengers']) for r in selected))
                    self.assertEqual(context['queue'], max(int(r['queue_passengers']) for r in selected))
                    self.assertEqual(context['wait'], max(float(r['estimated_wait_minutes']) for r in selected))
                    self.assertEqual(context['utilization'], max(float(r['utilization']) for r in selected_edges))

    def test_bad_rows_fail_closed(self):
        name = 'mobility_node_timeseries.csv'
        original = raw_rows(name)[0]
        for field, value in [('scenario_id', 'bad'), ('phase_id', 'bad'), ('node_id', ''),
                             ('data_type', 'provided'), ('queue_passengers', '-1'),
                             ('queue_passengers', '1.5'), ('utilization', 'nan'),
                             ('time_minutes', '3'), ('timestamp', 'invalid')]:
            with self.subTest(field=field, value=value), self.assertRaises((ValueError, TypeError)):
                validate_rows(name, [{**original, field: value}])
        with self.assertRaises(ValueError):
            validate_rows(name, [original, original])
        with self.assertRaises(ValueError):
            validate_rows(name, [{}])
        with self.assertRaises(ValueError):
            validate_rows(name, [])

    def test_missing_table_does_not_fallback_to_simulation(self):
        with patch('paddydash.services.finalflow_data.load_table', return_value=([], 'Missing export')):
            context = current_mobility('baseline', 0)
        self.assertFalse(context['available'])
        self.assertIsNone(context['queue'])
        self.assertIsNone(context['summary'])

    def test_catalog_only_effects_remain_missing(self):
        rows, error = load_table('intervention_comparison.csv')
        self.assertIsNone(error)
        for row in rows:
            if row['evaluation_status'] == 'catalog_only_not_modeled':
                self.assertIsNone(row['scenario_peak_queue_passengers'])
                self.assertEqual(row['comparison_scenario_id'], '')

    def test_recommendation_scope_and_missing_evidence(self):
        rules, _ = load_table('recommendation_catalog.csv')
        self.assertEqual(evaluate_rules(rules, {}), [])
        evidence = {'scenario_id': dict(value='rain', source_file='scenario_summary.csv', scope='Rain / halftime')}
        actions = evaluate_rules(rules, evidence)
        self.assertEqual(len(actions), 1)
        self.assertEqual(actions[0]['condition_id'], 'rain_scenario_selected')
        self.assertEqual(actions[0]['scope'], 'Rain / halftime')
        self.assertEqual(actions[0]['evidence_type'], 'synthetic')
        evidence['scenario_id']['value'] = None
        self.assertEqual(evaluate_rules(rules, evidence), [])

    def test_zero_baseline_and_phase_aliases(self):
        self.assertIsNone(percent_change(0, 10))
        self.assertEqual(percent_change(10, 10), 0)
        self.assertEqual(percent_change(10, 15), 50)
        for phase_id in ('kickoff', 'first_half', 'extra_time_end', 'final_whistle', 'post_match'):
            start, _, _ = phase_window(phase_id)
            self.assertTrue(current_mobility('baseline', start)['available'])


@patch.dict(os.environ, {'FINALFLOW_DISABLE_OPENAI': 'true', 'FINALFLOW_DISABLE_SEARCH': 'true'})
class AnalyticalPageTests(unittest.TestCase):
    def app(self, module, renderer):
        return AppTest.from_string(
            f'from paddydash.components.match_controls import render_match_controls\n'
            f'from paddydash.pages.{module} import {renderer}\n'
            f'render_match_controls()\n{renderer}()', default_timeout=30).run()

    def test_all_pages_canonical_phase_scenario_matrix(self):
        config = default_mobility_config()
        for module, renderer in PAGES:
            app = self.app(module, renderer)
            for scenario in config.scenarios:
                for phase in config.phases:
                    with self.subTest(page=module, scenario=scenario.scenario_id, phase=phase.phase_id):
                        app.selectbox(key='finalflow_scenario_id').set_value(scenario.scenario_id.value)
                        app.selectbox(key='finalflow_phase_id').set_value(phase.phase_id.value).run()
                        self.assertFalse(app.exception)
                        self.assertFalse(app.warning)
                        self.assertEqual(app.session_state['selected_phase_id'], phase.phase_id.value)
                        self.assertTrue(any('derived' in c.value.lower() or 'historical' in c.value.lower() for c in app.caption))

    def test_timeline_callback_and_scenario_preserve_minute(self):
        app = self.app('matchday_timeline', 'render_matchday_timeline')
        app.selectbox(key='timeline_phase').set_value('post_match').run()
        self.assertEqual(app.session_state['selected_phase_id'], 'post_match')
        app.slider(key='finalflow_time_widget').set_value(175).run()
        app.selectbox(key='finalflow_scenario_id').set_value('rain').run()
        self.assertEqual(app.session_state['finalflow_time_minutes'], 175)
        app.selectbox(key='timeline_phase').set_value('extra_time_end').run()
        self.assertEqual(app.session_state['finalflow_time_minutes'], 135)
        self.assertFalse(app.exception)

    def test_weather_windows_do_not_mix_denominators(self):
        app = self.app('weather_heat', 'render_weather_heat')
        figure = json.loads(app.get('plotly_chart')[0].proto.spec)
        self.assertEqual(len(figure['data'][0]['y']), 5)
        app.selectbox(key='weather_window').set_value('All months').run()
        figure = json.loads(app.get('plotly_chart')[0].proto.spec)
        self.assertEqual(len(figure['data'][0]['y']), 3)
        self.assertTrue(any('All months, 2020-2024' in c.value for c in app.caption))
        self.assertTrue(any('Low-visibility observation share is available' in c.value for c in app.caption))

    def test_empty_filters_and_commercial_subviews(self):
        for module, renderer, key in [('mobility', 'render_mobility', 'mobility_nodes'),
                                     ('scenario_explorer', 'render_scenario_explorer', 'lab_scenarios'),
                                     ('weather_heat', 'render_weather_heat', 'weather_heat')]:
            app = self.app(module, renderer)
            app.multiselect(key=key).set_value([]).run()
            self.assertFalse(app.exception)
            self.assertTrue(app.info)
        app = self.app('project_evidence', 'render_project_evidence')
        for label in ('POI & heat', 'Synthetic placement', 'Store visits'):
            app.radio(key='commercial_view').set_value(label).run()
            self.assertFalse(app.exception)
            self.assertGreater(len(app.get('plotly_chart')), 0)

    def test_missing_exports_leave_every_page_navigable(self):
        with patch('paddydash.services.finalflow_data.load_table', return_value=([], 'Missing export')):
            for module, renderer in PAGES:
                app = self.app(module, renderer)
                self.assertFalse(app.exception)
                self.assertTrue(app.title)


if __name__ == '__main__':
    unittest.main()
