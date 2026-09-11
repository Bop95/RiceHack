"""Demo controls, suggested questions and narrow failure-boundary regressions."""

import os
import unittest
from unittest.mock import patch

from streamlit.testing.v1 import AppTest

from paddydash.pages.ask_finalflow import SUGGESTIONS
from paddydash.services.project_context import selected_context, project_retrieval
from paddydash.services.mobility_config import default_mobility_config
from paddydash.services.search_service import should_search


@patch.dict(os.environ, {'OPENAI_API_KEY': '', 'SERPAPI_API_KEY': '',
                        'FINALFLOW_DISABLE_OPENAI': 'true', 'FINALFLOW_DISABLE_SEARCH': 'true'})
class DemoPolishTests(unittest.TestCase):
    def test_sidebar_controls_and_methodology(self):
        app = AppTest.from_file('paddydash/app.py', default_timeout=30).run()
        self.assertFalse(app.exception)
        labels = [item.label for item in app.sidebar.selectbox]
        self.assertIn('Match Phase', labels)
        self.assertIn('Scenario', labels)
        self.assertIn('About this data', [item.label for item in app.sidebar.expander])
        self.assertIn('Methodology & Assumptions', [item.label for item in app.expander])

    def test_suggestions_are_grounded_and_search_is_explicit(self):
        context = selected_context({'selected_scenario_id': 'rain'})
        for question in SUGGESTIONS:
            with self.subTest(question=question):
                if 'current transit' in question:
                    self.assertTrue(should_search(question))
                else:
                    self.assertFalse(should_search(question))
                    result = project_retrieval(question, None, context)
                    self.assertTrue(result.evidence)
                    self.assertIn('synthetic', result.local_answer)
        answer = project_retrieval('Which intervention performs best?', None, context).local_answer
        self.assertIn('No intervention is best across all objectives', answer)
        self.assertIn('tied at', answer)
        answer = project_retrieval('What changes after the final whistle?', None, context).local_answer
        self.assertIn('+130 to +140', answer)

    def test_assistant_all_canonical_selections_offline(self):
        app = AppTest.from_string('from paddydash.components.match_controls import render_match_controls\n'
                                 'from paddydash.pages.ask_finalflow import render_ask_finalflow\n'
                                 'render_match_controls()\nrender_ask_finalflow()', default_timeout=30).run()
        config = default_mobility_config()
        for scenario in config.scenarios:
            for phase in config.phases:
                with self.subTest(scenario=scenario.scenario_id, phase=phase.phase_id):
                    app.selectbox(key='finalflow_scenario_id').set_value(scenario.scenario_id.value)
                    app.selectbox(key='finalflow_phase_id').set_value(phase.phase_id.value).run()
                    self.assertFalse(app.exception)
                    self.assertTrue(app.chat_input)
                    self.assertEqual(app.session_state['selected_phase_id'], phase.phase_id.value)

    def test_page_failure_does_not_display_exception_content(self):
        source = '''
import streamlit as st
from paddydash.app import _safe_page
def broken():
    raise ValueError('private-error-detail')
_safe_page(broken)()
st.write('Navigation remains usable')
'''
        app = AppTest.from_string(source, default_timeout=30).run()
        self.assertFalse(app.exception)
        self.assertTrue(app.warning)
        self.assertNotIn('private-error-detail', ' '.join(item.value for item in app.caption))
        self.assertTrue(any('Navigation remains usable' in item.value for item in app.markdown))

    def test_scenario_metric_selector_retains_all_objectives(self):
        app = AppTest.from_string('from paddydash.pages.scenario_explorer import render_scenario_explorer\n'
                                 'render_scenario_explorer()', default_timeout=30).run()
        control = app.selectbox(key='lab_comparison_metric')
        self.assertEqual(len(control.options), 5)
        for option in control.options:
            app.selectbox(key='lab_comparison_metric').set_value(option).run()
            self.assertFalse(app.exception)
            self.assertEqual(len(app.get('plotly_chart')), 2)
