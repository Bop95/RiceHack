from backend.models.search_models import SearchResponse
from backend.services.serpapi_service import search_web
from fastapi import APIRouter, HTTPException, Query

router = APIRouter(prefix='/api', tags=['Search'])


@router.get('/search', response_model=SearchResponse)
async def get_search_results(q: str = Query(..., min_length=2)):
  if not q.strip():
    raise HTTPException(status_code=400, detail='Query cannot be empty.')

  return search_web(query=q)