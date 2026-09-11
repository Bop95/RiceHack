"""Mock-only checks for routed web context and independent project evidence."""

import json
import os
import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch

from streamlit.testing.v1 import AppTest

from paddydash.services.ai_service import attach_web_context, answer_with_fallback
from paddydash.services.project_context import selected_context, project_retrieval
from paddydash.services.search_models import SearchResponse, SearchResult
from paddydash.services.search_service import search_web, should_search


class SearchIntegrationTests(unittest.TestCase):
    def setUp(self):
        self.retrieval = project_retrieval('current simulated bottleneck', None, selected_context({}))
        self.source = SearchResult(title='Example transit advisory', link='https://example.org/advisory',
                                   source='example.org', snippet='An unverified test excerpt.', date='2026-07-19')
        self.search = SearchResponse(query='current transit advisory', results=[self.source], search_used=True)

    def test_explicit_router(self):
        for question in ['What is the bottleneck in the rail disruption scenario?',
                         'Which scenario has the lowest peak queue?',
                         'Why does staggered departure help?', 'What does our commercial chart show?',
                         'Do not search current transit alerts', 'current simulated transit queue']:
            with self.subTest(question=question):
                self.assertFalse(should_search(question))
        for question in ['Are there current NJ Transit disruptions?',
                         'What is the latest weather alert near the stadium?',
                         'Are there new venue access announcements?',
                         'What current public transit advisory is relevant?']:
            with self.subTest(question=question):
                self.assertTrue(should_search(question))

    def test_web_sources_reach_model_separately_and_cannot_change_metrics(self):
        retrieval = attach_web_context(self.retrieval, self.search)
        with patch.dict(os.environ, {'OPENAI_API_KEY': 'mock-openai', 'SERPAPI_API_KEY': 'mock-search'}, clear=True), patch('openai.OpenAI') as client:
            client.return_value.responses.parse.return_value = SimpleNamespace(
                output_parsed=SimpleNamespace(answer='Confirmed queue is 999999 passengers.', limitations=[]))
            response, _ = answer_with_fallback('current transit advisory', retrieval)
        request = client.return_value.responses.parse.call_args.kwargs
        external_context = request['input'][2]['content']
        self.assertIn(self.source.title, external_context)
        self.assertIn(self.source.snippet, external_context)
        self.assertIn('"data_type": "web"', external_context)
        self.assertNotIn('mock-search', repr(request))
        self.assertNotIn('mock-openai', repr(request))
        self.assertEqual(response.answer, self.retrieval.local_answer)
        self.assertEqual(response.evidence, self.retrieval.evidence)
        self.assertEqual(response.web_sources[0]['title'], self.source.title)
        self.assertEqual(response.web_status, 'available')
        self.assertTrue(response.search_used)
        json.dumps(response.to_dict())

    def test_openai_failure_retains_successful_search(self):
        retrieval = attach_web_context(self.retrieval, self.search)
        with patch.dict(os.environ, {'OPENAI_API_KEY': 'mock-openai'}, clear=True), patch('openai.OpenAI', side_effect=RuntimeError('mock-openai')):
            response, warning = answer_with_fallback('current transit advisory', retrieval)
        self.assertTrue(warning)
        self.assertNotIn('mock-openai', warning)
        self.assertEqual(response.answer, self.retrieval.local_answer)
        self.assertEqual(response.web_sources, [self.source.model_dump()])

    def test_failed_or_empty_search_preserves_project_answer(self):
        for used in [False, True]:
            search = SearchResponse(query='current transit advisory', results=[], search_used=used)
            retrieval = attach_web_context(self.retrieval, search)
            with patch.dict(os.environ, {'FINALFLOW_DISABLE_OPENAI': 'true'}):
                response, _ = answer_with_fallback('current transit advisory', retrieval)
            self.assertEqual(response.answer, self.retrieval.local_answer)
            self.assertEqual(response.web_sources, [])
            self.assertEqual(response.web_status, 'no_results' if used else 'unavailable')

    def test_normalization_and_result_limit(self):
        provider = Mock()
        provider.json.return_value = {'organic_results': [
            {'title': 'Notice', 'link': 'https://example.org/notice', 'snippet': 'Excerpt'}
        ] * 8}
        with patch.dict(os.environ, {'SERPAPI_API_KEY': 'mock-search'}, clear=True), patch('paddydash.services.search_service.requests.get', return_value=provider) as get:
            result = search_web('current transit advisory', num_results=10)
        self.assertEqual(len(result.results), 5)
        self.assertEqual(result.results[0].source, 'example.org')
        self.assertIsNone(result.results[0].date)
        self.assertEqual(get.call_args.kwargs['timeout'], 5.0)

    def test_ui_routes_search_and_displays_separate_sources(self):
        source = 'from paddydash.pages.ask_finalflow import render_ask_finalflow\nrender_ask_finalflow()'
        with patch.dict(os.environ, {'FINALFLOW_DISABLE_OPENAI': 'true', 'FINALFLOW_DISABLE_SEARCH': 'false'}):
            app = AppTest.from_string(source, default_timeout=30).run()
            with patch('paddydash.pages.ask_finalflow.search_web') as search:
                app.chat_input[0].set_value('What is the bottleneck in the rail disruption scenario?').run()
                search.assert_not_called()
            with patch('paddydash.pages.ask_finalflow.search_web', return_value=self.search) as search:
                app.chat_input[0].set_value('Are there current NJ Transit disruptions?').run()
                search.assert_called_once()
            self.assertFalse(app.exception)
            saved = app.session_state['chat_history'][-1]['response']
            self.assertEqual(saved['web_sources'][0]['title'], self.source.title)
            self.assertTrue(any(item.value == 'Web Sources' for item in app.subheader))
            self.assertTrue(any('Web search used' in item.value for item in app.markdown))
            self.assertTrue(any(item.label == 'Project Evidence' for item in app.expander))
            self.assertTrue(any(self.source.date in item.value for item in app.caption))
            self.assertTrue(app.get('link_button'))
