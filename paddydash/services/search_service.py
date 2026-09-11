"""Search and optional narration with safe, fixed provider failure responses."""

import os
import json
import re
import requests
try:
    from openai import OpenAI
except ImportError:
    OpenAI = None
from paddydash.services.search_models import SearchResponse, SearchResult


def summarize_search_results(query: str, search_context: str) -> str | None:
    """Uses OpenAI to generate a concise summary based on search result snippets."""
    api_key = os.getenv('OPENAI_API_KEY')
    if not api_key or OpenAI is None:
        return None

    prompt = f"""
    You are an AI assistant. Based on the following live web search results for the query "{query}",
    provide a concise, helpful synthesis for the user.

    Search Results Context:
    {search_context}
    """

    try:
        client = OpenAI(api_key=api_key)
        response = client.chat.completions.create(
            model='gpt-4o-mini',
            messages=[{'role': 'user', 'content': prompt}],
            temperature=0.7,
            max_tokens=300,
        )
        return response.choices[0].message.content.strip()
    except Exception:
        # Provider exceptions can contain credentials and request URLs.
        return None


def search_web(query: str, num_results: int = 5, *, summarize: bool = True) -> SearchResponse:
    """Executes a Google Search via SerpAPI and enriches the response with an OpenAI summary."""
    serpapi_key = os.getenv('SERPAPI_API_KEY', '').strip()

    disabled = os.getenv('FINALFLOW_DISABLE_SEARCH', '').lower() in ('true', '1', 'yes', 'on')
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
        snippets_for_ai = []

        for item in raw_results:
            serialized = json.dumps(item)
            if any(key and key in serialized for key in (serpapi_key, os.getenv('OPENAI_API_KEY', ''))):
                raise ValueError('Credential-like content in search response')
            title = item.get('title', 'No Title')
            snippet = item.get('snippet', '')

            normalized_results.append(
                SearchResult(
                    title=title,
                    link=item.get('link', ''),
                    source=item.get('source', 'Web'),
                    snippet=snippet,
                    date=item.get('date', None),
                )
            )
            if snippet:
                snippets_for_ai.append(f'- {title}: {snippet}')

        # Step 2: Summarize the results using OpenAI
        search_context = '\n'.join(snippets_for_ai)
        ai_summary = None
        if search_context and summarize:
            ai_summary = summarize_search_results(query, search_context)

        return SearchResponse(
            query=query,
            results=normalized_results,
            search_used=True,
            ai_summary=ai_summary,
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
    if re.search(r"simulat|model|scenario|bottleneck|queue|chart|prepared|our data|don't search|do not search|without (?:web|search)", text):
        return False
    current = re.search(r'\b(current|latest|today|live|recent|now)\b|up.to.date', text)
    public = re.search(r'\b(transit|rail|train|weather)\b|stadium.*(?:access|notice|alert)', text)
    return bool(current and public)
