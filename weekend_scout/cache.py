"""SQLite event cache and search log for Weekend Scout.

Database: <cache_dir>/cache.db

Tables:
  events      -- discovered events with dedup key
  search_log  -- record of web searches already performed
"""

from __future__ import annotations

import re
import sqlite3
from pathlib import Path
from typing import Any


CREATE_EVENTS = """
CREATE TABLE IF NOT EXISTS events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    event_name TEXT NOT NULL,
    city TEXT NOT NULL,
    country TEXT DEFAULT 'PL',
    start_date TEXT NOT NULL,
    end_date TEXT,
    time_info TEXT,
    location_name TEXT,
    lat REAL,
    lon REAL,
    category TEXT,
    description TEXT,
    free_entry BOOLEAN,
    source_url TEXT,
    source_name TEXT,
    discovered_date TEXT NOT NULL,
    confidence TEXT DEFAULT 'likely',
    served BOOLEAN DEFAULT 0,
    canceled BOOLEAN DEFAULT 0,
    dedup_key TEXT UNIQUE
);
"""

CREATE_SEARCH_LOG = """
CREATE TABLE IF NOT EXISTS search_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    query TEXT NOT NULL,
    search_date TEXT NOT NULL,
    target_weekend TEXT NOT NULL,
    result_count INTEGER DEFAULT 0,
    cities_covered TEXT,
    phase TEXT
);
"""

CREATE_INDEXES = """
CREATE INDEX IF NOT EXISTS idx_events_dates ON events(start_date, end_date);
CREATE INDEX IF NOT EXISTS idx_events_city ON events(city);
CREATE INDEX IF NOT EXISTS idx_events_dedup ON events(dedup_key);
CREATE INDEX IF NOT EXISTS idx_search_log_weekend ON search_log(target_weekend);
"""


def get_db_path(config: dict[str, Any]) -> Path:
    """Return the path to the SQLite database file.

    Args:
        config: Loaded configuration dictionary.

    Returns:
        Path to cache.db.
    """
    pass


def get_connection(config: dict[str, Any]) -> sqlite3.Connection:
    """Open (and if necessary initialise) the SQLite database.

    Args:
        config: Loaded configuration dictionary.

    Returns:
        Open sqlite3.Connection with schema applied.
    """
    pass


def dedup_key(event_name: str, city: str, start_date: str) -> str:
    """Generate a normalised dedup key for an event.

    Key format: <normalised_name>_<normalised_city>_<start_date>

    Args:
        event_name: Raw event name.
        city: City name.
        start_date: ISO date string.

    Returns:
        Lowercase alphanumeric dedup key string.
    """
    name = re.sub(r"[^a-z0-9]", "", event_name.lower())
    city_clean = re.sub(r"[^a-z0-9]", "", city.lower())
    return f"{name}_{city_clean}_{start_date}"


def save_events(
    config: dict[str, Any], events: list[dict[str, Any]]
) -> tuple[int, int]:
    """Save a list of events to the cache, skipping duplicates.

    Args:
        config: Loaded configuration dictionary.
        events: List of event dicts matching the events table schema.

    Returns:
        Tuple of (saved_count, skipped_count).
    """
    pass


def query_events(
    config: dict[str, Any], saturday: str
) -> list[dict[str, Any]]:
    """Return cached events for the weekend starting on the given Saturday.

    Includes events whose start_date or end_date falls on Saturday or Sunday.

    Args:
        config: Loaded configuration dictionary.
        saturday: ISO date string of target Saturday.

    Returns:
        List of event dicts.
    """
    pass


def log_search(
    config: dict[str, Any],
    query: str,
    target_weekend: str,
    result_count: int,
    cities_covered: list[str],
    phase: str,
) -> None:
    """Record a completed web search in the search log.

    Args:
        config: Loaded configuration dictionary.
        query: The search query string.
        target_weekend: ISO date of the target Saturday.
        result_count: Number of results the search returned.
        cities_covered: City names covered by this search.
        phase: Search phase label ('broad', 'aggregator', 'targeted', 'verification').
    """
    pass


def get_searches_this_week(
    config: dict[str, Any], saturday: str
) -> list[str]:
    """Return query strings already logged for the target weekend this week.

    Args:
        config: Loaded configuration dictionary.
        saturday: ISO date string of target Saturday.

    Returns:
        List of query strings.
    """
    pass


def mark_served(config: dict[str, Any], saturday: str) -> int:
    """Mark all events for the target weekend as served (sent to Telegram).

    Args:
        config: Loaded configuration dictionary.
        saturday: ISO date string of target Saturday.

    Returns:
        Number of rows updated.
    """
    pass


def cleanup_old_events(config: dict[str, Any], days: int = 30) -> int:
    """Delete events older than `days` days from the cache.

    Args:
        config: Loaded configuration dictionary.
        days: Age threshold in days (default 30).

    Returns:
        Number of rows deleted.
    """
    pass
