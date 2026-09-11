"""Offline integration checks using existing prepared tables, never live providers."""

import os
import unittest
from types import SimpleNamespace
from unittest.mock import patch
from streamlit.testing.v1 import AppTest
from paddydash.services.project_context import selected_context, project_retrieval
from paddydash.services.data_service import load_dashboard_data
from paddydash.services.finalflow_data import load_table
from paddydash.services.search_service import should_search, search_web
from paddydash.services.search_models import SearchResult
from paddydash.services.ai_service import prepared_data_response, answer_with_openai


class ProjectContextTests(unittest.TestCase):
    def test_stale_snapshot_ignored(self):
        context = selected_context({'finalflow_phase_id': 'post_match', 'finalflow_scenario_id': 'rail_disruption',
                                    'finalflow_time_minutes': -135, 'finalflow_time_selection': ('pre_match', 'baseline')})
        self.assertEqual(context['time_minutes'], 165)
        self.assertGreater(context['queue'], 0)

    def test_current_facts_and_comparison(self):
        context = selected_context({})
        result = project_retrieval('which scenario has the lowest queue?', load_dashboard_data(), context)
        summaries, _ = load_table('scenario_summary.csv')
        minimum = min(r['peak_queue_passengers'] for r in summaries)
        self.assertIn(f'tied at {minimum:,}', result.local_answer)
        self.assertEqual(prepared_data_response(result).answer, result.local_answer)

    def test_search_routing(self):
        for question in ['current transit alert', 'current weather alert', 'latest stadium access notice']:
            self.assertTrue(should_search(question))
        for question in ['current simulated bottleneck?', 'which scenario has the lowest queue?', 'what does this chart show?', 'do not search current weather']:
            self.assertFalse(should_search(question))

    def test_fabricated_model_queue_cannot_override_simulator(self):
        result = project_retrieval('current bottleneck?', load_dashboard_data(), selected_context({}))
        with patch.dict(os.environ, {'OPENAI_API_KEY': 'test-only'}, clear=True), patch('openai.OpenAI') as client:
            client.return_value.responses.parse.return_value = SimpleNamespace(
                output_parsed=SimpleNamespace(answer='The queue is 999999 people.', limitations=[]))
            response = answer_with_openai('current bottleneck?', result)
        self.assertEqual(response.answer, result.local_answer)
        self.assertNotIn('999999', response.answer)

    def test_search_offline_and_unsafe_url(self):
        with patch.dict(os.environ, {'FINALFLOW_DISABLE_SEARCH': '1'}), patch('paddydash.services.search_service.requests.get') as provider:
            self.assertFalse(search_web('current transit alert').search_used)
            provider.assert_not_called()
        for url in ['javascript:alert(1)', 'https://example.org/?api_key=secret', 'https://user:pass@example.org']:
            with self.assertRaises(ValueError):
                SearchResult(title='Notice', link=url)

    @patch.dict(os.environ, {'FINALFLOW_DISABLE_OPENAI': '1', 'FINALFLOW_DISABLE_SEARCH': '1', 'OPENAI_API_KEY': '', 'SERPAPI_API_KEY': ''})
    def test_context_page_and_offline_assistant(self):
        for module, function in [('project_evidence', 'render_project_evidence'), ('ask_finalflow', 'render_ask_finalflow')]:
            app = AppTest.from_string(f'from paddydash.pages.{module} import {function}\n{function}()', default_timeout=30).run()
            self.assertFalse(app.exception)
            if module == 'ask_finalflow':
                app.chat_input[0].set_value('why did the recommendation change?').run()
                self.assertFalse(app.exception)
                self.assertIn('Modeled bottleneck', app.session_state['chat_history'][-1]['response']['answer'])
