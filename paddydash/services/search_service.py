"""Bounded public search with safe, fixed provider failure responses."""

import os
import json
import re
from html import unescape
from urllib.parse import unquote_plus, urlsplit
import requests
from paddydash.services.search_models import SearchResponse, SearchResult


def summarize_search_results(query: str, search_context: str) -> str | None:
    """Compatibility hook: AI context now goes through the guarded assistant only.

    Retained for Tan Dat's backend imports. Avoid a second, unguarded provider call.
    """
    return None


def search_web(query: str, num_results: int = 5, *, summarize: bool = False) -> SearchResponse:
    """Fetch up to five bounded public snippets; legacy summarize is a no-op."""
    serpapi_key = os.getenv('SERPAPI_API_KEY', '').strip()

    disabled = os.getenv('FINALFLOW_DISABLE_SEARCH', '').strip().lower() in ('true', '1', 'yes', 'on')
    if not serpapi_key or disabled:
        return SearchResponse(
            query=query,
            results=[],
            search_used=False,
            ai_summary=None,
            error='Search service unavailable',
        )

    params = {
        'q': query,
        'api_key': serpapi_key,
        'engine': 'google',
        'num': max(1, min(num_results, 5)),
    }

    try:
        # Step 1: Fetch live search results from SerpAPI
        response = requests.get(
            'https://serpapi.com/search', params=params, timeout=5.0
        )
        response.raise_for_status()
        data = response.json()
        if not isinstance(data, dict) or 'error' in data:
            raise ValueError('Invalid search response')

        raw_results = data.get('organic_results', [])
        if not isinstance(raw_results, list):
            raise ValueError('Invalid search results')
        raw_results = raw_results[:max(1, min(num_results, 5))]
        normalized_results = []

        for item in raw_results:
            if not isinstance(item, dict):
                raise ValueError('Invalid source record')
            serialized = json.dumps(item)
            for _ in range(3):
                serialized = unescape(unquote_plus(serialized))
            if any(key and key in serialized for key in (serpapi_key, os.getenv('OPENAI_API_KEY', ''))):
                raise ValueError('Credential-like content in search response')
            if re.search(r'(?:api[_-]?key|access[_-]?token|serpapi_api_key|openai_api_key|aws_secret_access_key)\s*[=:]', serialized, re.I):
                raise ValueError('Credential-like content in search response')
            title = item.get('title', 'No Title')
            snippet = item.get('snippet', '')

            normalized_results.append(
                SearchResult(
                    title=title,
                    link=item.get('link', ''),
                    source=item.get('source') or urlsplit(item.get('link', '')).hostname,
                    snippet=snippet,
                    date=item.get('date', None),
                )
            )

        return SearchResponse(
            query=query,
            results=normalized_results,
            search_used=True,
            ai_summary=None,
            error=None,
        )

    except Exception:
        # Never return or log exception text, response bodies, or request URLs.
        return SearchResponse(
            query=query,
            results=[],
            search_used=False,
            ai_summary=None,
            error='Search service unavailable',
        )


def should_search(question: str) -> bool:
    """Explicit current public-information requests only; never model questions."""
    text = question.casefold()
    if re.search(r"simulat|model|scenario|bottleneck|queue|chart|prepared|our data|staggered departure|don't search|do not search|without (?:web|search)", text):
        return False
    current = re.search(r'\b(current|latest|today|live|recent|new|now)\b|up.to.date', text)
    public = re.search(r'\b(transit|rail|train|weather)\b|(?:stadium|venue).*(?:access|notice|alert|announcement)', text)
    return bool(current and public)
