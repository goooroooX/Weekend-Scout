"""Tests for run-scoped session candidate persistence."""

import pytest


@pytest.fixture
def cfg(tmp_path):
    return {"home_city": "Warsaw", "radius_km": 150, "_cache_dir": str(tmp_path)}


def test_session_query_returns_current_weekend_and_preserves_future_candidates(cfg):
    from weekend_scout.session_cache import (
        export_session_candidates,
        query_session_candidates,
        upsert_session_candidates,
    )

    upsert_session_candidates(
        cfg,
        "2026-04-04_1200",
        "2026-04-04",
        [
            {"event_name": "Weekend Fest", "city": "Berlin", "start_date": "2026-04-04"},
            {"event_name": "Future Fest", "city": "Berlin", "start_date": "2026-04-18"},
        ],
    )

    all_candidates = export_session_candidates(cfg, "2026-04-04_1200")
    weekend_candidates = query_session_candidates(cfg, "2026-04-04_1200")

    assert [candidate["event_name"] for candidate in all_candidates] == ["Weekend Fest", "Future Fest"]
    assert weekend_candidates == [
        {"event_name": "Weekend Fest", "city": "Berlin", "start_date": "2026-04-04"}
    ]


def test_session_upsert_upgrades_confidence_and_corrects_weekend_dates(cfg):
    from weekend_scout.session_cache import export_session_candidates, upsert_session_candidates

    first = upsert_session_candidates(
        cfg,
        "2026-04-04_1200",
        "2026-04-04",
        [
            {
                "event_name": "River Parade",
                "city": "Berlin",
                "start_date": "2026-04-04",
                "time_info": "10:00",
                "source_url": "https://aggregator.example/parade",
                "confidence": "likely",
            }
        ],
    )
    second = upsert_session_candidates(
        cfg,
        "2026-04-04_1200",
        "2026-04-04",
        [
            {
                "event_name": "River Parade",
                "city": "Berlin",
                "start_date": "2026-04-05",
                "time_info": "12:00",
                "source_url": "https://official.example/parade",
                "confidence": "confirmed",
            }
        ],
    )

    assert first["events_discovered"] == 1
    assert second["events_discovered"] == 0

    candidates = export_session_candidates(cfg, "2026-04-04_1200")
    assert len(candidates) == 1
    assert candidates[0]["start_date"] == "2026-04-05"
    assert candidates[0]["time_info"] == "12:00"
    assert candidates[0]["source_url"] == "https://official.example/parade"
    assert candidates[0]["confidence"] == "confirmed"


def test_weaker_later_hits_do_not_erase_stronger_session_candidate_data(cfg):
    from weekend_scout.session_cache import export_session_candidates, upsert_session_candidates

    upsert_session_candidates(
        cfg,
        "2026-04-04_1200",
        "2026-04-04",
        [
            {
                "event_name": "Night Market",
                "city": "Berlin",
                "start_date": "2026-04-04",
                "location_name": "Central Square",
                "source_url": "https://official.example/market",
                "confidence": "confirmed",
            }
        ],
    )
    upsert_session_candidates(
        cfg,
        "2026-04-04_1200",
        "2026-04-04",
        [
            {
                "event_name": "Night Market",
                "city": "Berlin",
                "start_date": "2026-04-04",
                "location_name": "Wrong Place",
                "source_url": "https://aggregator.example/market",
                "free_entry": True,
                "confidence": "likely",
            }
        ],
    )

    candidates = export_session_candidates(cfg, "2026-04-04_1200")
    assert candidates == [
        {
            "event_name": "Night Market",
            "city": "Berlin",
            "start_date": "2026-04-04",
            "location_name": "Central Square",
            "source_url": "https://official.example/market",
            "free_entry": True,
            "confidence": "confirmed",
        }
    ]
