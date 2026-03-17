"""
Stock universe state — loaded once from Supabase on startup.

Provides symbol list, company names, and sectors for the rest of the application.
Extracted from analytics.py to break circular dependencies between service modules.
"""

from __future__ import annotations

import logging
from ..data.stock_repository import load_universe

logger = logging.getLogger(__name__)

NIFTY_INDEX = "^NSEI"

_symbols: list[str] = []
_names: dict[str, str] = {}
_sectors: dict[str, str] = {}
_loaded = False


def load() -> None:
    """Fetch universe from Supabase and populate module state."""
    global _symbols, _names, _sectors, _loaded
    _symbols, _names, _sectors = load_universe()
    _loaded = True


def _ensure_loaded() -> None:
    if not _loaded:
        load()


def get_symbols() -> list[str]:
    """Return all stock symbols with .NS suffix (e.g. 'RELIANCE.NS')."""
    _ensure_loaded()
    return _symbols


def get_name(symbol: str) -> str:
    _ensure_loaded()
    return _names.get(symbol, symbol)


def get_sector(symbol: str) -> str:
    _ensure_loaded()
    return _sectors.get(symbol, "Unknown")


def get_names() -> dict[str, str]:
    _ensure_loaded()
    return _names


def get_sectors() -> dict[str, str]:
    _ensure_loaded()
    return _sectors
