"""Tests for weekend_scout.cache."""

import datetime
import json
import pytest


@pytest.fixture
def cfg(tmp_path):
    """Config with _cache_dir pointing to a temp directory."""
    return {"home_city": "Warsaw", "radius_km": 150, "_cache_dir": str(tmp_path)}


def _event(**kwargs):
    """Return a minimal valid event dict, overridable via kwargs."""
    base = {
        "event_name": "Test Fest",
        "city": "Warsaw",
        "start_date": "2026-04-04",
        "category": "festival",
        "confidence": "likely",
    }
    base.update(kwargs)
    return base


# --- dedup_key ---

def test_dedup_key_normalises():
    from weekend_scout.cache import dedup_key
    key = dedup_key("Jarmark Wielkanocny", "Warsaw", "2026-03-28")
    assert key == "jarmark_wielkanocny_warsaw_2026-03-28"


def test_dedup_key_no_space_collision():
    from weekend_scout.cache import dedup_key
    key_spaced = dedup_key("Dni Miasta", "Warsaw", "2026-03-28")
    key_joined = dedup_key("DniMiasta", "Warsaw", "2026-03-28")
    assert key_spaced != key_joined


def test_dedup_key_strips_special_chars():
    from weekend_scout.cache import dedup_key
    key = dedup_key("Festiwal Łódź 2026", "Łódź", "2026-03-28")
    assert "_" in key
    assert all(c.isalnum() or c in "_-" for c in key)


# --- get_db_path ---

def test_get_db_path_uses_cache_dir_override(cfg, tmp_path):
    from weekend_scout.cache import get_db_path
    path = get_db_path(cfg)
    assert path.parent == tmp_path
    assert path.name == "cache.db"


# --- get_connection / schema ---

def test_get_connection_creates_tables(cfg):
    from weekend_scout.cache import get_connection
    conn = get_connection(cfg)
    tables = {r[0] for r in conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table'"
    ).fetchall()}
    assert "events" in tables
    assert "search_log" in tables
    conn.close()


def test_get_connection_idempotent(cfg):
    from weekend_scout.cache import get_connection
    # Calling twice should not raise
    conn1 = get_connection(cfg)
    conn1.close()
    conn2 = get_connection(cfg)
    conn2.close()


# --- save_events ---

def test_save_events_returns_counts(cfg):
    from weekend_scout.cache import save_events
    events = [_event(start_date="2026-04-04"), _event(event_name="Other Fest", start_date="2026-04-04")]
    saved, skipped = save_events(cfg, events)
    assert saved == 2
    assert skipped == 0


def test_save_events_deduplicates(cfg):
    from weekend_scout.cache import save_events
    event = _event()
    save_events(cfg, [event])
    saved, skipped = save_events(cfg, [event])
    assert saved == 0
    assert skipped == 1


def test_save_events_exact_key_collision_upgrades_missing_fields(cfg):
    from weekend_scout.cache import get_connection, save_events

    save_events(
        cfg,
        [_event(country="", confidence="likely", source_name=None, source_url=None, location_name=None)],
    )
    saved, skipped = save_events(
        cfg,
        [
            _event(
                country="Poland",
                confidence="confirmed",
                source_name="Official",
                source_url="https://example.com/fest",
                location_name="Main Square",
                description="Confirmed details",
            )
        ],
    )

    assert saved == 0
    assert skipped == 1
    with get_connection(cfg) as conn:
        row = conn.execute("SELECT * FROM events WHERE event_name = 'Test Fest'").fetchone()
    assert row["country"] == "Poland"
    assert row["confidence"] == "confirmed"
    assert row["source_name"] == "Official"
    assert row["source_url"] == "https://example.com/fest"
    assert row["location_name"] == "Main Square"
    assert row["description"] == "Confirmed details"


def test_save_events_stores_optional_fields(cfg):
    from weekend_scout.cache import save_events, get_connection
    event = _event(
        end_date="2026-04-05",
        location_name="Rynek",
        free_entry=True,
        source_url="https://example.com",
        confidence="confirmed",
    )
    save_events(cfg, [event])
    conn = get_connection(cfg)
    row = conn.execute("SELECT * FROM events WHERE event_name = 'Test Fest'").fetchone()
    assert row["end_date"] == "2026-04-05"
    assert row["location_name"] == "Rynek"
    assert row["free_entry"] == 1
    assert row["confidence"] == "confirmed"
    conn.close()


# --- query_events ---

def test_query_events_returns_list(cfg):
    from weekend_scout.cache import save_events, query_events
    save_events(cfg, [_event(start_date="2026-04-04")])
    result = query_events(cfg, "2026-04-04")
    assert isinstance(result, list)
    assert len(result) == 1
    assert result[0]["event_name"] == "Test Fest"


def test_query_events_covers_saturday_and_sunday(cfg):
    from weekend_scout.cache import save_events, query_events
    save_events(cfg, [
        _event(event_name="Sat Event", start_date="2026-04-04"),
        _event(event_name="Sun Event", start_date="2026-04-05"),
    ])
    result = query_events(cfg, "2026-04-04")
    names = {e["event_name"] for e in result}
    assert "Sat Event" in names
    assert "Sun Event" in names


def test_query_events_includes_multi_day_spanning_weekend(cfg):
    from weekend_scout.cache import save_events, query_events
    # Event starts before and ends after the whole weekend — must be included
    save_events(cfg, [_event(event_name="Long Fest",
                             start_date="2026-03-20", end_date="2026-04-10")])
    result = query_events(cfg, "2026-04-04")
    assert len(result) == 1
    assert result[0]["event_name"] == "Long Fest"


def test_query_events_excludes_other_weekends(cfg):
    from weekend_scout.cache import save_events, query_events
    save_events(cfg, [_event(start_date="2026-04-11")])  # next weekend
    result = query_events(cfg, "2026-04-04")
    assert result == []


def test_query_events_exclude_served_filters_served(cfg):
    from weekend_scout.cache import save_events, query_events, get_connection
    save_events(cfg, [_event(event_name="Old", start_date="2026-04-04")])
    with get_connection(cfg) as conn:
        conn.execute("UPDATE events SET served = 1")
    cfg_excl = dict(cfg, exclude_served=True)
    result = query_events(cfg_excl, "2026-04-04")
    assert result == []


def test_query_events_exclude_served_false_includes_served(cfg):
    from weekend_scout.cache import save_events, query_events, get_connection
    save_events(cfg, [_event(event_name="Old", start_date="2026-04-04")])
    with get_connection(cfg) as conn:
        conn.execute("UPDATE events SET served = 1")
    result = query_events(cfg, "2026-04-04")  # default False
    assert len(result) == 1


def test_query_events_excludes_canceled(cfg):
    from weekend_scout.cache import save_events, query_events, get_connection
    save_events(cfg, [_event(start_date="2026-04-04")])
    with get_connection(cfg) as conn:
        conn.execute("UPDATE events SET canceled = 1")
    result = query_events(cfg, "2026-04-04")
    assert result == []


def test_query_events_summary_returns_compact_counts(cfg):
    from weekend_scout.cache import save_events, query_events_summary
    save_events(cfg, [
        _event(event_name="A", city="Berlin", start_date="2026-04-04"),
        _event(event_name="B", city="Berlin", start_date="2026-04-05"),
        _event(event_name="C", city="Potsdam", start_date="2026-04-04"),
    ])
    summary = query_events_summary(cfg, "2026-04-04")
    assert summary["count"] == 3
    assert summary["covered_cities"] == ["Berlin", "Potsdam"]
    assert summary["city_counts"] == {"Berlin": 2, "Potsdam": 1}


def test_query_events_summary_exclude_served_matches_query_events(cfg):
    from weekend_scout.cache import save_events, query_events_summary, get_connection
    save_events(cfg, [_event(event_name="Old", city="Berlin", start_date="2026-04-04")])
    with get_connection(cfg) as conn:
        conn.execute("UPDATE events SET served = 1")
    cfg_excl = dict(cfg, exclude_served=True)
    summary = query_events_summary(cfg_excl, "2026-04-04")
    assert summary == {"count": 0, "covered_cities": [], "city_counts": {}}


def test_query_events_summary_excludes_canceled(cfg):
    from weekend_scout.cache import save_events, query_events_summary, get_connection
    save_events(cfg, [_event(event_name="Gone", city="Berlin", start_date="2026-04-04")])
    with get_connection(cfg) as conn:
        conn.execute("UPDATE events SET canceled = 1")
    summary = query_events_summary(cfg, "2026-04-04")
    assert summary == {"count": 0, "covered_cities": [], "city_counts": {}}


# --- log_search / get_searches_this_week ---

def test_log_search_inserts_row(cfg):
    from weekend_scout.cache import log_search, get_searches_this_week
    log_search(cfg, "test query", "2026-04-04", 5, ["Warsaw"], "broad")
    queries = get_searches_this_week(cfg, "2026-04-04")
    assert "test query" in queries


def test_get_searches_this_week_returns_queries(cfg):
    from weekend_scout.cache import log_search, get_searches_this_week
    log_search(cfg, "query one", "2026-04-04", 3, [], "broad")
    log_search(cfg, "query two", "2026-04-04", 7, ["Łódź"], "targeted")
    queries = get_searches_this_week(cfg, "2026-04-04")
    assert set(queries) == {"query one", "query two"}


def test_get_searches_this_week_different_weekend(cfg):
    from weekend_scout.cache import log_search, get_searches_this_week
    log_search(cfg, "old query", "2026-03-28", 2, [], "broad")
    queries = get_searches_this_week(cfg, "2026-04-04")
    assert queries == []


# --- mark_served ---

def test_mark_served_updates_rows(cfg):
    from weekend_scout.cache import save_events, mark_served, query_events, get_connection
    save_events(cfg, [
        _event(event_name="A", start_date="2026-04-04"),
        _event(event_name="B", start_date="2026-04-05"),
    ])
    count = mark_served(cfg, "2026-04-04")
    assert count == 2
    with get_connection(cfg) as conn:
        unserved = conn.execute("SELECT COUNT(*) FROM events WHERE served = 0").fetchone()[0]
    assert unserved == 0


def test_mark_served_only_target_weekend(cfg):
    from weekend_scout.cache import save_events, mark_served, get_connection
    save_events(cfg, [
        _event(event_name="This Wknd", start_date="2026-04-04"),
        _event(event_name="Next Wknd", start_date="2026-04-11"),
    ])
    mark_served(cfg, "2026-04-04")
    with get_connection(cfg) as conn:
        next_served = conn.execute(
            "SELECT served FROM events WHERE event_name = 'Next Wknd'"
        ).fetchone()["served"]
    assert next_served == 0


# --- cleanup_old_events ---

def test_cleanup_old_events_removes_stale(cfg):
    from weekend_scout.cache import save_events, cleanup_old_events, get_connection
    old_date = (datetime.date.today() - datetime.timedelta(days=60)).isoformat()
    save_events(cfg, [_event(start_date=old_date)])
    deleted = cleanup_old_events(cfg, days=30)
    assert deleted == 1
    with get_connection(cfg) as conn:
        count = conn.execute("SELECT COUNT(*) FROM events").fetchone()[0]
    assert count == 0


def test_cleanup_old_events_keeps_recent(cfg):
    from weekend_scout.cache import save_events, cleanup_old_events
    save_events(cfg, [_event(start_date="2026-04-04")])
    deleted = cleanup_old_events(cfg, days=30)
    assert deleted == 0


# --- log_action ---

def test_log_action_creates_file(cfg, tmp_path):
    from weekend_scout.cache import log_action
    log_action(cfg, "test_action", target_weekend="2026-04-04")
    log_file = tmp_path / "action_log.jsonl"
    assert log_file.exists()


def test_log_action_appends(cfg, tmp_path):
    from weekend_scout.cache import log_action
    log_action(cfg, "action_one")
    log_action(cfg, "action_two")
    lines = (tmp_path / "action_log.jsonl").read_text(encoding="utf-8").splitlines()
    assert len(lines) == 2


def test_log_action_valid_json(cfg, tmp_path):
    from weekend_scout.cache import log_action
    log_action(cfg, "phase_start", phase="A", run_id="2026-04-04_1200",
               source="skill", target_weekend="2026-04-04",
               detail={"events_found": 3})
    line = (tmp_path / "action_log.jsonl").read_text(encoding="utf-8").strip()
    entry = json.loads(line)
    assert entry["action"] == "phase_start"
    assert entry["phase"] == "A"
    assert entry["run_id"] == "2026-04-04_1200"
    assert entry["source"] == "skill"
    assert entry["target_weekend"] == "2026-04-04"
    assert entry["detail"]["events_found"] == 3
    assert "ts" in entry


def test_log_search_also_writes_jsonl(cfg, tmp_path):
    from weekend_scout.cache import log_search
    log_search(cfg, "test query", "2026-04-04", 5, ["Warsaw"], "broad",
               run_id="2026-04-04_1200")
    log_file = tmp_path / "action_log.jsonl"
    assert log_file.exists()
    entry = json.loads(log_file.read_text(encoding="utf-8").strip())
    assert entry["action"] == "search"
    assert entry["phase"] == "broad"
    assert entry["detail"]["query"] == "test query"
    assert entry["detail"]["result_count"] == 5
    assert entry["detail"]["events_discovered"] == 0


def test_log_search_events_discovered_field(cfg, tmp_path):
    from weekend_scout.cache import log_search
    log_search(cfg, "some query", "2026-04-04", 3, ["Lodz"], "targeted",
               run_id="2026-04-04_1200", events_discovered=4)
    log_file = tmp_path / "action_log.jsonl"
    entry = json.loads(log_file.read_text(encoding="utf-8").strip())
    assert entry["detail"]["events_discovered"] == 4


def test_log_search_stores_run_id_and_events_discovered(cfg):
    from weekend_scout.cache import log_search, get_connection
    log_search(cfg, "query x", "2026-04-04", 5, ["Warsaw"], "broad",
               run_id="run-123", events_discovered=7)
    with get_connection(cfg) as conn:
        row = conn.execute(
            "SELECT run_id, events_discovered FROM search_log WHERE query = ?",
            ("query x",)
        ).fetchone()
    assert row["run_id"] == "run-123"
    assert row["events_discovered"] == 7


def test_log_search_returns_duplicate_merge_counts(cfg):
    from weekend_scout.cache import log_search

    first = log_search(
        cfg,
        "berlin one",
        "2026-04-11",
        3,
        ["Berlin"],
        "targeted",
        run_id="2026-04-11_2151",
        events=[
            {
                "event_name": "Berliner Staudenmarkt",
                "city": "Berlin",
                "start_date": "2026-04-11",
                "end_date": "2026-04-12",
                "source_url": "https://visitberlin.example/markets",
                "confidence": "likely",
            }
        ],
    )
    second = log_search(
        cfg,
        "berlin two",
        "2026-04-11",
        3,
        ["Berlin"],
        "verification",
        run_id="2026-04-11_2151",
        events=[
            {
                "event_name": "Berliner Staudenmarkt auf der Domäne Dahlem",
                "city": "Berlin",
                "start_date": "2026-04-11",
                "end_date": "2026-04-12",
                "source_url": "https://visitberlin.example/markets",
                "confidence": "confirmed",
            }
        ],
    )

    assert first == {
        "events_discovered": 1,
        "session_candidate_count": 1,
        "duplicates_merged": 0,
    }
    assert second == {
        "events_discovered": 0,
        "session_candidate_count": 1,
        "duplicates_merged": 1,
    }
