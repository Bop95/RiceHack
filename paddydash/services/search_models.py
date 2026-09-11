from typing import List, Optional
from pydantic import BaseModel, Field
from pydantic import field_validator
from urllib.parse import parse_qs, urlsplit


class SearchResult(BaseModel):
  title: str = Field(min_length=1, max_length=240)
  link: str = Field(min_length=1, max_length=2048)
  source: Optional[str] = Field(default=None, max_length=240)
  snippet: Optional[str] = Field(default=None, max_length=1200)
  date: Optional[str] = Field(default=None, max_length=100)

  @field_validator('link')
  @classmethod
  def public_url(cls, value: str) -> str:
    url = urlsplit(value)
    sensitive = {'api_key', 'apikey', 'key', 'token', 'access_token', 'secret',
                 'serpapi_api_key', 'openai_api_key', 'aws_secret_access_key',
                 'x-amz-credential', 'x-amz-signature'}
    if (url.scheme not in ('https', 'http') or not url.hostname or url.username
        or url.password or sensitive.intersection(k.lower() for k in parse_qs(url.query, keep_blank_values=True))
        or sensitive.intersection(k.lower() for k in parse_qs(url.fragment, keep_blank_values=True))):
      raise ValueError('Unsafe search source URL')
    return value


class SearchResponse(BaseModel):
  query: str
  results: List[SearchResult]
  search_used: bool
  ai_summary: Optional[str] = None  # Legacy field; narration belongs to the guarded assistant.
  error: Optional[str] = None
