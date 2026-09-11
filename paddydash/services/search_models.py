from typing import List, Optional
from pydantic import BaseModel
from pydantic import field_validator
from urllib.parse import parse_qs, urlsplit


class SearchResult(BaseModel):
  title: str
  link: str
  source: Optional[str] = None
  snippet: Optional[str] = None
  date: Optional[str] = None

  @field_validator('link')
  @classmethod
  def public_url(cls, value: str) -> str:
    url = urlsplit(value)
    sensitive = {'api_key', 'apikey', 'key', 'token', 'access_token', 'secret'}
    if (url.scheme not in ('https', 'http') or not url.hostname or url.username
        or url.password or sensitive.intersection(k.lower() for k in parse_qs(url.query))):
      raise ValueError('Unsafe search source URL')
    return value


class SearchResponse(BaseModel):
  query: str
  results: List[SearchResult]
  search_used: bool
  ai_summary: Optional[str] = None  # New field for OpenAI response
  error: Optional[str] = None
