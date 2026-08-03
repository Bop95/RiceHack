from typing import List, Optional
from pydantic import BaseModel


class SearchResult(BaseModel):
  title: str
  link: str
  source: Optional[str] = None
  snippet: Optional[str] = None
  date: Optional[str] = None


class SearchResponse(BaseModel):
  query: str
  results: List[SearchResult]
  search_used: bool
  error: Optional[str] = None