"""Offline checks that provider failures never disclose credentials."""

import os
import unittest
from unittest.mock import Mock, patch

import requests


from paddydash.services import search_service as service


class SearchServiceSecurityTests(unittest.TestCase):
    def setUp(self) -> None:
        self.secret = 'test-provider-secret-not-a-real-key'
        self.url = 'https://serpapi.com/search?api_key=' + self.secret
        environment = patch.dict(os.environ, {'SERPAPI_API_KEY': self.secret}, clear=True)
        environment.start()
        self.addCleanup(environment.stop)

    def assert_safe_failure(self, response: Mock | None = None,
                            error: Exception | None = None) -> None:
        # Any raised exception or log record fails the test; no raw exceptions
        # should escape even when providers include secrets in their messages.
        with self.assertNoLogs(level='DEBUG'):
            with patch.object(service.requests, 'get', return_value=response,
                              side_effect=error):
                result = service.search_web('Weather at the stadium')
        payload = result.model_dump_json()
        self.assertNotIn(self.secret, payload)
        self.assertNotIn(self.url, payload)
        self.assertNotIn('api_key=', payload)
        self.assertEqual(result.error, 'Search service unavailable')
        self.assertFalse(result.search_used)
        self.assertEqual(result.results, [])
        self.assertIsNone(result.ai_summary)

    def test_provider_400_error(self) -> None:
        response = requests.Response()
        response.status_code = 400
        response.url = self.url
        self.assert_safe_failure(response=response)

    def test_provider_500_error(self) -> None:
        response = requests.Response()
        response.status_code = 500
        response.url = self.url
        self.assert_safe_failure(response=response)

    def test_timeout(self) -> None:
        self.assert_safe_failure(error=requests.Timeout(self.url))

    def test_connection_error(self) -> None:
        self.assert_safe_failure(error=requests.ConnectionError(self.url))

    def test_malformed_response(self) -> None:
        response = Mock()
        response.json.side_effect = ValueError(self.url)
        self.assert_safe_failure(response=response)
        for body in (None, [], {'error': self.url}, {'organic_results': None},
                     {'organic_results': 'invalid'}, {'organic_results': [self.url]}):
            with self.subTest(body=type(body).__name__):
                response = Mock()
                response.json.return_value = body
                self.assert_safe_failure(response=response)

    def test_missing_api_key(self) -> None:
        for value in ('', '   '):
            with self.subTest(value=value):
                with patch.dict(os.environ, {'SERPAPI_API_KEY': value}, clear=True):
                    with self.assertNoLogs(level='DEBUG'):
                        with patch.object(service.requests, 'get') as get:
                            result = service.search_web('Weather')
                    get.assert_not_called()
                    self.assertFalse(result.search_used)
                    self.assertEqual(result.error, 'Search service unavailable')
                    self.assertNotIn(self.secret, result.model_dump_json())

    def test_summary_errors_do_not_leak_or_discard_search_sources(self) -> None:
        response = Mock()
        response.json.return_value = {'organic_results': [
            {'title': 'Weather', 'link': 'https://example.org/weather', 'snippet': 'Cloudy'}
        ]}
        for fail_in_constructor in (True, False):
            with self.subTest(fail_in_constructor=fail_in_constructor):
                with patch.dict(os.environ, {'OPENAI_API_KEY': self.secret}):
                    with self.assertNoLogs(level='DEBUG'):
                        with patch.object(service.requests, 'get', return_value=response):
                            with patch.object(service, 'OpenAI') as client:
                                if fail_in_constructor:
                                    client.side_effect = RuntimeError(self.url)
                                else:
                                    client.return_value.chat.completions.create.side_effect = RuntimeError(self.url)
                                result = service.search_web('Weather')
                self.assertTrue(result.search_used)
                self.assertEqual(len(result.results), 1)
                self.assertIsNone(result.ai_summary)
                self.assertNotIn(self.secret, result.model_dump_json())

    def test_empty_search_results_are_a_valid_response(self) -> None:
        response = Mock()
        response.json.return_value = {'organic_results': []}
        with patch.object(service.requests, 'get', return_value=response):
            result = service.search_web('Weather')
        self.assertTrue(result.search_used)
        self.assertIsNone(result.error)


if __name__ == '__main__':
    unittest.main()
