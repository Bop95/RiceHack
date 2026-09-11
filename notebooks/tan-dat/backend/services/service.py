import os
import requests
from openai import OpenAI
from backend.models.search_models import SearchResponse, SearchResult


def summarize_search_results(query: str, search_context: str) -> str:
    """Uses OpenAI to generate a concise summary based on search result snippets."""
    api_key = os.getenv('OPENAI_API_KEY')
    if not api_key:
        return 'OpenAI API key is missing from environment variables.'

    client = OpenAI(api_key=api_key)

    prompt = f"""
    You are an AI assistant. Based on the following live web search results for the query "{query}", 
    provide a concise, helpful synthesis for the user.

    Search Results Context:
    {search_context}
    """

    try:
        response = client.chat.completions.create(
            model='gpt-4o-mini',
            messages=[{'role': 'user', 'content': prompt}],
            temperature=0.7,
            max_tokens=300,
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        return f'Failed to generate AI summary: {str(e)}'


def search_web(query: str, num_results: int = 5) -> SearchResponse:
    """Executes a Google Search via SerpAPI and enriches the response with an OpenAI summary."""
    serpapi_key = os.getenv('SERPAPI_API_KEY')

    if not serpapi_key:
        return SearchResponse(
            query=query,
            results=[],
            search_used=False,
            ai_summary=None,
            error='SERPAPI_API_KEY is not set in backend environment variables.',
        )

    params = {
        'q': query,
        'api_key': serpapi_key,
        'engine': 'google',
        'num': num_results,
    }

    try:
        # Step 1: Fetch live search results from SerpAPI
        response = requests.get(
            'https://serpapi.com/search', params=params, timeout=5.0
        )
        response.raise_for_status()
        data = response.json()

        raw_results = data.get('organic_results', [])[:num_results]
        normalized_results = []
        snippets_for_ai = []

        for item in raw_results:
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
        if search_context:
            ai_summary = summarize_search_results(query, search_context)

        return SearchResponse(
            query=query,
            results=normalized_results,
            search_used=True,
            ai_summary=ai_summary,
            error=None,
        )

    except requests.exceptions.Timeout:
        return SearchResponse(
            query=query,
            results=[],
            search_used=False,
            ai_summary=None,
            error='SerpAPI request timed out.',
        )
    except Exception as e:
        return SearchResponse(
            query=query,
            results=[],
            search_used=False,
            ai_summary=None,
            error=str(e),
        )