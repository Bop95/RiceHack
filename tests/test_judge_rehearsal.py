"""Offline judge journey: replay controls, contextual evidence and safe search."""

import os
import unittest
from unittest.mock import Mock, patch

from streamlit.testing.v1 import AppTest

from paddydash.services.project_context import selected_context


SOURCE = '''
import streamlit as st
from paddydash.components.match_controls import render_match_controls
from paddydash.pages.mobility import render_mobility
from paddydash.pages.project_evidence import render_project_evidence
from paddydash.pages.ask_finalflow import render_ask_finalflow
render_match_controls()
view = st.radio('Rehearsal view', ['Mobility', 'Evidence', 'Assistant'])
{'Mobility': render_mobility, 'Evidence': render_project_evidence,
 'Assistant': render_ask_finalflow}[view]()
'''


class JudgeRehearsalTests(unittest.TestCase):
    def setUp(self):
        environment = patch.dict(os.environ, {
            'FINALFLOW_DISABLE_OPENAI': 'true', 'FINALFLOW_DISABLE_SEARCH': 'false',
            'OPENAI_API_KEY': '', 'SERPAPI_API_KEY': 'test-search-only',
        })
        environment.start()
        self.addCleanup(environment.stop)

    def ask(self, app, question):
        app.text_area[0].set_value(question)
        next(b for b in app.button if b.label == 'Ask FinalFlow').click().run()
        self.assertFalse(app.exception)
        return app.session_state['chat_history'][-1]

    def test_phase_scenario_matrix_matches_engine(self):
        app = AppTest.from_string(SOURCE, default_timeout=30).run()
        for scenario in ('baseline', 'rain', 'rail_disruption'):
            for phase in ('pre_match', 'kickoff', 'final_whistle', 'post_match'):
                with self.subTest(scenario=scenario, phase=phase):
                    app.selectbox(key='finalflow_scenario_id').set_value(scenario)
                    app.selectbox(key='finalflow_phase_id').set_value(phase).run()
                    self.assertFalse(app.exception)
                    context = selected_context(dict(app.session_state.filtered_state))
                    metrics = {m.label: m.value for m in app.metric}
                    self.assertEqual(metrics['Largest node queue'], f"{context['queue']:,}")
                    self.assertEqual(metrics['Current utilization'], f"{context['utilization']:.0%}")
                    self.assertEqual(metrics['Post-match clearance'], f"{context['run'].clearance_minutes} min")
                    wait = max(n.estimated_wait_minutes for n in context['snapshot'].node_states)
                    self.assertEqual(metrics['Estimated longest wait'], f'{wait:.0f} min')
                    if not context['queue']:
                        self.assertEqual(metrics['Bottleneck'], 'None')
                    else:
                        self.assertNotEqual(metrics['Bottleneck'], 'None')
                    comparison = app.dataframe[1].value
                    self.assertEqual(comparison.iloc[0]['Selected scenario'], context['run'].peak_queue)
                    self.assertEqual(app.session_state['finalflow_mobility_snapshot'], context['snapshot'].model_dump(mode='json'))

    def test_navigation_history_and_external_sources(self):
        app = AppTest.from_string(SOURCE, default_timeout=30).run()
        app.selectbox(key='finalflow_phase_id').set_value('post_match')
        app.selectbox(key='finalflow_scenario_id').set_value('rain').run()
        scope = selected_context(dict(app.session_state.filtered_state))['scope']
        app.radio[0].set_value('Evidence').run()
        self.assertFalse(app.exception)
        self.assertTrue(any(scope in c.value for c in app.caption))
        app.radio[0].set_value('Assistant').run()
        with patch('paddydash.services.search_service.requests.get') as provider:
            answer = self.ask(app, 'why did the recommendation change?')
            provider.assert_not_called()
        self.assertEqual(answer['scope'], scope)
        self.assertIn('covered waiting', answer['response']['answer'])
        app.selectbox(key='finalflow_scenario_id').set_value('rail_disruption').run()
        self.assertEqual(app.session_state['chat_history'][0]['scope'], scope)
        with patch('paddydash.services.search_service.requests.get') as provider:
            answer = self.ask(app, 'which scenario has the lowest queue?')
            provider.assert_not_called()
        self.assertIn('tied at 0', answer['response']['answer'])
        response = Mock()
        response.json.return_value = {'organic_results': [
            {'title': 'Test transit notice', 'link': 'https://example.org/notice', 'snippet': 'Mock external notice.'}
        ]}
        for question in ('current transit alert', 'current weather alert', 'latest stadium access notice'):
            with patch('paddydash.services.search_service.requests.get', return_value=response) as provider:
                answer = self.ask(app, question)
                provider.assert_called_once()
            self.assertTrue(answer['web']['search_used'])
            self.assertEqual(answer['web']['results'][0]['link'], 'https://example.org/notice')
            self.assertNotIn('Mock external notice', answer['response']['answer'])
            self.assertTrue(app.get('link_button'))
        with patch.dict(os.environ, {'SERPAPI_API_KEY': ''}), patch('paddydash.services.search_service.requests.get') as provider:
            answer = self.ask(app, 'current transit alert')
            provider.assert_not_called()
        self.assertFalse(answer['web']['search_used'])
        self.assertTrue(any('Search is unavailable' in i.value for i in app.info))


if __name__ == '__main__':
    unittest.main()
