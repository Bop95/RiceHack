"""Compatibility imports for the shared search response contract."""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from paddydash.services.search_models import SearchResponse, SearchResult  # noqa: E402,F401
