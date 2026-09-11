"""Offline regression checks for match-aware chat; providers are always mocked."""

import json
import os
import unittest
from types import SimpleNamespace
from unittest.mock import patch

from streamlit.testing.v1 import AppTest

from paddydash.pages.ask_finalflow import response_to_state, response_from_state
from paddydash.services.ai_service import answer_with_fallback, answer_with_openai
from paddydash.services.project_context import project_retrieval, question_context, selected_context


class AskFinalFlowTests(unittest.TestCase):
    def setUp(self):
        self.context = selected_context({'selected_phase_id': 'final_whistle',
                                         'selected_scenario_id': 'rail_disruption'})
        self.retrieval = project_retrieval('Why is this scenario worse?', None, self.context)

    def test_missing_key_and_structured_round_trip(self):
        with patch.dict(os.environ, {}, clear=True), patch('openai.OpenAI') as provider:
            response, warning = answer_with_fallback('Why?', self.retrieval)
        provider.assert_not_called()
        self.assertIsNone(warning)
        self.assertEqual(response.answer, self.retrieval.local_answer)
        state = json.loads(json.dumps(response_to_state(response)))
        self.assertEqual(response_from_state(state), response)
        self.assertTrue(state['key_findings'])
        self.assertTrue(all(item['data_type'] == 'derived' for item in state['evidence']))

    def test_scope_in_model_request_and_fabrication_rejected(self):
        with patch.dict(os.environ, {'OPENAI_API_KEY': 'secret-test'}, clear=True), patch('openai.OpenAI') as provider:
            provider.return_value.responses.parse.return_value = SimpleNamespace(
                output_parsed=SimpleNamespace(answer='The queue is 999999 people.', limitations=[]))
            response = answer_with_openai('Why?', self.retrieval)
        prompt = provider.return_value.responses.parse.call_args.kwargs['input'][0]['content']
        self.assertIn('Final whistle', prompt)
        self.assertIn('Rail disruption', prompt)
        self.assertNotIn('secret-test', prompt)
        self.assertNotIn('999999', response.answer)
        self.assertEqual(response.evidence, self.retrieval.evidence)

    def test_malformed_and_provider_errors_use_silent_prepared_fallback(self):
        for parsed in [None, SimpleNamespace(answer=12, limitations=[]),
                       SimpleNamespace(answer='text', limitations='invalid')]:
            with self.subTest(parsed=parsed), patch.dict(os.environ, {'OPENAI_API_KEY': 'secret-test'}, clear=True), patch('openai.OpenAI') as provider:
                provider.return_value.responses.parse.return_value = SimpleNamespace(output_parsed=parsed)
                response, warning = answer_with_fallback('Why?', self.retrieval)
                self.assertIsNone(warning)
                self.assertEqual(response.answer, self.retrieval.local_answer)
        with patch.dict(os.environ, {'OPENAI_API_KEY': 'secret-test'}, clear=True), patch('openai.OpenAI', side_effect=RuntimeError('secret-test')):
            response, warning = answer_with_fallback('Why?', self.retrieval)
        self.assertIsNone(warning)
        self.assertNotIn('secret-test', repr((response, warning)))

    def test_explicit_scope_does_not_mutate_selection(self):
        original = selected_context({})
        scoped = question_context('Bottleneck at final whistle during rail disruption?', original)
        self.assertEqual(scoped['phase_id'], 'final_whistle')
        self.assertEqual(scoped['scenario_id'], 'rail_disruption')
        self.assertEqual(scoped['time_minutes'], 135)
        self.assertEqual(original['phase_id'], 'pre_match')

    def test_baseline_comparison_keeps_selected_scenario(self):
        scoped = question_context('How does this scenario compare with baseline?', self.context)
        self.assertEqual(scoped['scenario_id'], 'rail_disruption')
        scoped = question_context('What is the baseline bottleneck?', self.context)
        self.assertEqual(scoped['scenario_id'], 'baseline')

    def test_clear_preserves_global_scope_and_allowance(self):
        source = 'from paddydash.pages.ask_finalflow import render_ask_finalflow\nrender_ask_finalflow()'
        with patch.dict(os.environ, {'FINALFLOW_DISABLE_OPENAI': 'true', 'FINALFLOW_DISABLE_SEARCH': 'true'}):
            app = AppTest.from_string(source, default_timeout=30).run()
            app.session_state['selected_phase_id'] = 'final_whistle'
            app.session_state['ai_request_count'] = 3
            app.chat_input[0].set_value('What is the bottleneck?').run()
            self.assertFalse(app.exception)
            self.assertEqual(len(app.session_state['chat_history']), 1)
            next(button for button in app.button if button.label == 'Clear conversation').click().run()
            self.assertFalse(app.exception)
            self.assertEqual(app.session_state['chat_history'], [])
            self.assertEqual(app.session_state['selected_phase_id'], 'final_whistle')
            self.assertEqual(app.session_state['ai_request_count'], 3)

    def test_context_budget_fails_closed(self):
        from dataclasses import replace
        oversized = replace(self.retrieval, context='x' * 18001)
        with patch.dict(os.environ, {'OPENAI_API_KEY': 'secret-test'}, clear=True), patch('openai.OpenAI') as provider:
            answer_with_openai('Why?', oversized)
        provider.assert_not_called()
