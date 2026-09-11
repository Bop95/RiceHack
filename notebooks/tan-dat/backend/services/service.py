"""Compatibility imports for Tan Dat's backend; the app owns the shared service."""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from paddydash.services.search_service import search_web, summarize_search_results  # noqa: E402,F401
