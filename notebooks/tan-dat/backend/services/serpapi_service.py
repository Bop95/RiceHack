import os
import requests
from backend.models.search_models import SearchResponse, SearchResult


def search_web(query: str, num_results: int = 5) -> SearchResponse:
  api_key = os.getenv('SERPAPI_API_KEY')

  if not api_key:
    return SearchResponse(
        query=query,
        results=[],
        search_used=False,
        error='SERPAPI_API_KEY is not set in backend environment variables.',
    )

  params = {
      'q': query,
      'api_key': api_key,
      'engine': 'google',
      'num': num_results,
  }

  try:
    response = requests.get(
        'https://serpapi.com/search', params=params, timeout=5.0
    )
    response.raise_for_status()
    data = response.json()

    raw_results = data.get('organic_results', [])[:num_results]
    normalized_results = []

    for item in raw_results:
      normalized_results.append(
          SearchResult(
              title=item.get('title', 'No Title'),
              link=item.get('link', ''),
              source=item.get('source', 'Web'),
              snippet=item.get('snippet', ''),
              date=item.get('date', None),
          )
      )

    return SearchResponse(
        query=query, results=normalized_results, search_used=True, error=None
    )

  except requests.exceptions.Timeout:
    return SearchResponse(
        query=query,
        results=[],
        search_used=False,
        error='SerpAPI request timed out.',
    )
  except Exception as e:
    return SearchResponse(
        query=query, results=[], search_used=False, error=str(e)
    )