"""Tests for weekend_scout.cache."""

import sqlite3
import pytest


@pytest.fixture
def in_memory_config(tmp_path):
    """Config pointing to a temp directory (in-memory DB via :memory: override)."""
    return {"home_city": "Warsaw", "radius_km": 150, "_cache_dir": str(tmp_path)}


def test_dedup_key_normalises():
    from weekend_scout.cache import dedup_key
    key = dedup_key("Jarmark Wielkanocny", "Warsaw", "2026-03-28")
    assert key == "jarmarkwielkanocny_warsaw_2026-03-28"


def test_dedup_key_strips_special_chars():
    from weekend_scout.cache import dedup_key
    key = dedup_key("Festiwal Łódź 2026", "Łódź", "2026-03-28")
    assert "_" in key
    assert key.islower() or key.replace("_", "").replace("-", "").isalnum()


def test_save_events_returns_counts():
    pass


def test_save_events_deduplicates():
    pass


def test_query_events_returns_list():
    pass


def test_query_events_covers_saturday_and_sunday():
    pass


def test_log_search_inserts_row():
    pass


def test_get_searches_this_week_returns_queries():
    pass


def test_mark_served_updates_rows():
    pass


def test_cleanup_old_events_removes_stale():
    pass
