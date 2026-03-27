"""SQLite event cache and search log for Weekend Scout.

Database: <cache_dir>/cache.db

Tables:
  events      -- discovered events with dedup key
  search_log  -- record of web searches already performed
"""

from __future__ import annotations

import datetime
import json
import re
import sqlite3
from pathlib import Path
from typing import Any


CREATE_EVENTS = """
CREATE TABLE IF NOT EXISTS events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    event_name TEXT NOT NULL,
    city TEXT NOT NULL,
    country TEXT DEFAULT '',
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

    Respects the `_cache_dir` override key for testing.

    Args:
        config: Loaded configuration dictionary.

    Returns:
        Path to cache.db.
    """
    if "_cache_dir" in config:
        cache_dir = Path(config["_cache_dir"])
    else:
        from weekend_scout.config import get_cache_dir
        cache_dir = get_cache_dir(config)
    return cache_dir / "cache.db"


def get_connection(config: dict[str, Any]) -> sqlite3.Connection:
    """Open (and if necessary initialise) the SQLite database.

    Runs CREATE TABLE / INDEX statements on every open — all use
    IF NOT EXISTS so this is safe to call repeatedly.

    Args:
        config: Loaded configuration dictionary.

    Returns:
        Open sqlite3.Connection with row_factory set to sqlite3.Row.
    """
    db_path = get_db_path(config)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    conn.executescript(CREATE_EVENTS + CREATE_SEARCH_LOG + CREATE_INDEXES)
    conn.commit()
    return conn


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
    name = re.sub(r"[^\w]", "", event_name.lower())
    city_clean = re.sub(r"[^\w]", "", city.lower())
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
    saved = 0
    skipped = 0
    today = datetime.date.today().isoformat()

    with get_connection(config) as conn:
        for event in events:
            key = dedup_key(
                event["event_name"], event["city"], event["start_date"]
            )
            cursor = conn.execute(
                """
                INSERT OR IGNORE INTO events (
                    event_name, city, country, start_date, end_date, time_info,
                    location_name, lat, lon, category, description, free_entry,
                    source_url, source_name, discovered_date, confidence,
                    served, canceled, dedup_key
                ) VALUES (
                    :event_name, :city, :country, :start_date, :end_date, :time_info,
                    :location_name, :lat, :lon, :category, :description, :free_entry,
                    :source_url, :source_name, :discovered_date, :confidence,
                    :served, :canceled, :dedup_key
                )
                """,
                {
                    "event_name": event["event_name"],
                    "city": event["city"],
                    "country": event.get("country", ""),
                    "start_date": event["start_date"],
                    "end_date": event.get("end_date"),
                    "time_info": event.get("time_info"),
                    "location_name": event.get("location_name"),
                    "lat": event.get("lat"),
                    "lon": event.get("lon"),
                    "category": event.get("category"),
                    "description": event.get("description"),
                    "free_entry": event.get("free_entry"),
                    "source_url": event.get("source_url"),
                    "source_name": event.get("source_name"),
                    "discovered_date": today,
                    "confidence": event.get("confidence", "likely"),
                    "served": 0,
                    "canceled": 0,
                    "dedup_key": key,
                },
            )
            if cursor.rowcount > 0:
                saved += 1
            else:
                skipped += 1

    return saved, skipped


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
    sunday = (
        datetime.date.fromisoformat(saturday) + datetime.timedelta(days=1)
    ).isoformat()

    with get_connection(config) as conn:
        rows = conn.execute(
            """
            SELECT * FROM events
            WHERE (start_date IN (?, ?) OR end_date IN (?, ?))
              AND canceled = 0
            ORDER BY start_date, city
            """,
            (saturday, sunday, saturday, sunday),
        ).fetchall()

    return [dict(row) for row in rows]


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
    today = datetime.date.today().isoformat()
    with get_connection(config) as conn:
        conn.execute(
            """
            INSERT INTO search_log
                (query, search_date, target_weekend, result_count, cities_covered, phase)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (query, today, target_weekend, result_count,
             json.dumps(cities_covered), phase),
        )


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
    with get_connection(config) as conn:
        rows = conn.execute(
            "SELECT query FROM search_log WHERE target_weekend = ?",
            (saturday,),
        ).fetchall()
    return [row["query"] for row in rows]


def mark_served(config: dict[str, Any], saturday: str) -> int:
    """Mark all events for the target weekend as served (sent to Telegram).

    Args:
        config: Loaded configuration dictionary.
        saturday: ISO date string of target Saturday.

    Returns:
        Number of rows updated.
    """
    sunday = (
        datetime.date.fromisoformat(saturday) + datetime.timedelta(days=1)
    ).isoformat()

    with get_connection(config) as conn:
        cursor = conn.execute(
            """
            UPDATE events SET served = 1
            WHERE (start_date IN (?, ?) OR end_date IN (?, ?))
              AND served = 0
            """,
            (saturday, sunday, saturday, sunday),
        )
    return cursor.rowcount


def cleanup_old_events(config: dict[str, Any], days: int = 30) -> int:
    """Delete events older than `days` days from the cache.

    Args:
        config: Loaded configuration dictionary.
        days: Age threshold in days (default 30).

    Returns:
        Number of rows deleted.
    """
    cutoff = (
        datetime.date.today() - datetime.timedelta(days=days)
    ).isoformat()

    with get_connection(config) as conn:
        cursor = conn.execute(
            "DELETE FROM events WHERE start_date < ?",
            (cutoff,),
        )
    return cursor.rowcount
