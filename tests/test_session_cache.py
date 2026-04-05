"""Tests for run-scoped session candidate persistence."""

import pytest


@pytest.fixture
def cfg(tmp_path):
    return {
        "home_city": "Warsaw",
        "home_country": "Poland",
        "radius_km": 150,
        "_cache_dir": str(tmp_path),
    }


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


def test_session_enriches_home_city_country(tmp_path):
    from weekend_scout.session_cache import export_session_candidates, upsert_session_candidates

    config = {
        "home_city": "Berlin",
        "home_country": "Germany",
        "radius_km": 150,
        "_cache_dir": str(tmp_path),
    }
    upsert_session_candidates(
        config,
        "2026-04-04_1200",
        "2026-04-04",
        [{"event_name": "Spring Fest", "city": "Berlin", "start_date": "2026-04-04"}],
    )

    candidates = export_session_candidates(config, "2026-04-04_1200")
    assert candidates == [
        {
            "event_name": "Spring Fest",
            "city": "Berlin",
            "country": "Germany",
            "start_date": "2026-04-04",
        }
    ]


def test_session_enriches_country_from_city_metadata(cfg, monkeypatch):
    import weekend_scout.cities as cities_module
    from weekend_scout.session_cache import export_session_candidates, upsert_session_candidates

    cfg = dict(cfg, home_coordinates={"lat": 52.2297, "lon": 21.0122})
    monkeypatch.setattr(
        cities_module,
        "get_city_list",
        lambda _cfg: {"tier1": [], "tier2": [], "tier3": ["Szczecin|PL"]},
    )

    upsert_session_candidates(
        cfg,
        "2026-04-04_1200",
        "2026-04-04",
        [{"event_name": "Harbor Fest", "city": "Szczecin", "start_date": "2026-04-04"}],
    )

    candidates = export_session_candidates(cfg, "2026-04-04_1200")
    assert candidates == [
        {
            "event_name": "Harbor Fest",
            "city": "Szczecin",
            "country": "Poland",
            "start_date": "2026-04-04",
        }
    ]


def test_session_merges_berliner_staudenmarkt_aliases(cfg):
    from weekend_scout.session_cache import export_session_candidates, upsert_session_candidates

    first = upsert_session_candidates(
        cfg,
        "2026-04-11_2151",
        "2026-04-11",
        [
            {
                "event_name": "Berliner Staudenmarkt",
                "city": "Berlin",
                "start_date": "2026-04-11",
                "end_date": "2026-04-12",
                "category": "market",
                "source_url": "https://www.visitberlin.de/de/kategorie/festivals-maerkte",
                "source_name": "visitBerlin",
                "confidence": "likely",
            }
        ],
    )
    second = upsert_session_candidates(
        cfg,
        "2026-04-11_2151",
        "2026-04-11",
        [
            {
                "event_name": "Berliner Staudenmarkt auf der Domäne Dahlem",
                "city": "Berlin",
                "start_date": "2026-04-11",
                "end_date": "2026-04-12",
                "category": "market",
                "source_url": "https://www.visitberlin.de/de/kategorie/festivals-maerkte",
                "source_name": "visitBerlin",
                "confidence": "confirmed",
            }
        ],
    )

    assert first["events_discovered"] == 1
    assert second["events_discovered"] == 0
    assert second["duplicates_merged"] == 1
    candidates = export_session_candidates(cfg, "2026-04-11_2151")
    assert candidates == [
        {
            "event_name": "Berliner Staudenmarkt auf der Domäne Dahlem",
            "city": "Berlin",
            "start_date": "2026-04-11",
            "end_date": "2026-04-12",
            "category": "market",
            "source_url": "https://www.visitberlin.de/de/kategorie/festivals-maerkte",
            "source_name": "visitBerlin",
            "confidence": "confirmed",
        }
    ]


def test_session_merges_kirschbluetenfest_aliases(cfg):
    from weekend_scout.session_cache import export_session_candidates, upsert_session_candidates

    upsert_session_candidates(
        cfg,
        "2026-04-11_2151",
        "2026-04-11",
        [
            {
                "event_name": "Kirschblütenfest in den Gärten der Welt",
                "city": "Berlin",
                "start_date": "2026-04-11",
                "end_date": "2026-04-12",
                "category": "festival",
                "source_url": "https://www.berlin.de/events/jahresuebersicht/april/",
                "source_name": "Berlin.de",
                "confidence": "likely",
            },
            {
                "event_name": "Sakura – Kirschblütenfest in den Gärten der Welt",
                "city": "Berlin",
                "start_date": "2026-04-11",
                "end_date": "2026-04-12",
                "category": "festival",
                "source_url": "https://www.visitberlin.de/de/kategorie/festivals-maerkte",
                "source_name": "visitBerlin",
                "confidence": "confirmed",
            },
        ],
    )

    candidates = export_session_candidates(cfg, "2026-04-11_2151")
    assert candidates == [
        {
            "event_name": "Sakura – Kirschblütenfest in den Gärten der Welt",
            "city": "Berlin",
            "start_date": "2026-04-11",
            "end_date": "2026-04-12",
            "category": "festival",
            "source_url": "https://www.visitberlin.de/de/kategorie/festivals-maerkte",
            "source_name": "visitBerlin",
            "confidence": "confirmed",
        }
    ]
