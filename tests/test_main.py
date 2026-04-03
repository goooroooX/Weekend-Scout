"""Tests for weekend_scout.__main__ CLI commands."""

import json
import sys
import pytest
from pathlib import Path


@pytest.fixture
def patched_config(tmp_path, monkeypatch):
    """Redirect config module to a temp directory for isolation."""
    import weekend_scout.config as cfg_module
    config_file = tmp_path / "config.yaml"
    monkeypatch.setattr(cfg_module, "get_config_path", lambda: config_file)
    monkeypatch.setattr(cfg_module, "get_config_dir", lambda: tmp_path)
    return tmp_path


def _run_config(args: list[str], tmp_path, monkeypatch) -> dict:
    """Helper: call cmd_config with given args, return parsed JSON output."""
    import weekend_scout.config as cfg_module
    config_file = tmp_path / "config.yaml"
    monkeypatch.setattr(cfg_module, "get_config_path", lambda: config_file)
    monkeypatch.setattr(cfg_module, "get_config_dir", lambda: tmp_path)

    from weekend_scout.__main__ import build_parser, COMMANDS
    parser = build_parser()
    parsed = parser.parse_args(["config"] + args)

    captured = []
    monkeypatch.setattr("builtins.print", lambda *a, **kw: captured.append(a[0]))
    try:
        COMMANDS["config"](parsed)
    except SystemExit:
        pass
    return json.loads(captured[-1])


# --- config (no args) ---

def test_cmd_config_shows_all_keys(tmp_path, monkeypatch):
    result = _run_config([], tmp_path, monkeypatch)
    assert "home_city" in result
    assert "radius_km" in result
    assert "search_language" in result


def test_cmd_config_search_language_default_en(tmp_path, monkeypatch):
    result = _run_config([], tmp_path, monkeypatch)
    assert result["search_language"] == "en"


# --- config KEY (read single key) ---

def test_cmd_config_read_single_key(tmp_path, monkeypatch):
    result = _run_config(["radius_km"], tmp_path, monkeypatch)
    assert result == {"radius_km": 150}


def test_cmd_config_read_string_key(tmp_path, monkeypatch):
    result = _run_config(["search_language"], tmp_path, monkeypatch)
    assert result == {"search_language": "en"}


def test_cmd_config_read_unknown_key_returns_error(tmp_path, monkeypatch):
    result = _run_config(["nonexistent_key"], tmp_path, monkeypatch)
    assert "error" in result


# --- config KEY VALUE (set) ---

def test_cmd_config_set_string_value(tmp_path, monkeypatch):
    result = _run_config(["home_city", "Krakow"], tmp_path, monkeypatch)
    assert result == {"set": {"home_city": "Krakow"}}
    # Verify persisted
    result2 = _run_config(["home_city"], tmp_path, monkeypatch)
    assert result2 == {"home_city": "Krakow"}


def test_cmd_config_set_int_value_coerces_type(tmp_path, monkeypatch):
    result = _run_config(["radius_km", "200"], tmp_path, monkeypatch)
    assert result == {"set": {"radius_km": 200}}
    assert isinstance(result["set"]["radius_km"], int)


def test_cmd_config_set_unknown_key_returns_error(tmp_path, monkeypatch):
    result = _run_config(["bad_key", "value"], tmp_path, monkeypatch)
    assert "error" in result


# --- format-message ---

def _run_format_message(args: list[str], tmp_path, monkeypatch) -> dict:
    """Helper: call cmd_format_message, return parsed JSON output."""
    import weekend_scout.config as cfg_module
    config_file = tmp_path / "config.yaml"
    monkeypatch.setattr(cfg_module, "get_config_path", lambda: config_file)
    monkeypatch.setattr(cfg_module, "get_config_dir", lambda: tmp_path)

    from weekend_scout.__main__ import build_parser, COMMANDS
    parser = build_parser()
    parsed = parser.parse_args(["format-message"] + args)

    captured = []
    monkeypatch.setattr("builtins.print", lambda *a, **kw: captured.append(a[0]))
    COMMANDS["format-message"](parsed)
    return json.loads(captured[-1])


def test_format_message_creates_file(tmp_path, monkeypatch):
    output = tmp_path / "msg.txt"
    result = _run_format_message(
        ["--saturday", "2026-03-28", "--sunday", "2026-03-29", "--output", str(output)],
        tmp_path, monkeypatch,
    )
    assert result["written"] == str(output)
    assert "preview" in result
    assert output.exists()


def test_format_message_with_events(tmp_path, monkeypatch):
    import json as _json
    output = tmp_path / "msg.txt"
    events = _json.dumps([{
        "event_name": "Spring Festival", "city": "Warsaw",
        "start_date": "2026-03-28", "free_entry": True,
    }])
    _run_format_message(
        ["--saturday", "2026-03-28", "--sunday", "2026-03-29",
         "--city-events", events, "--output", str(output)],
        tmp_path, monkeypatch,
    )
    content = output.read_text(encoding="utf-8")
    assert "Spring Festival" in content
    assert "Weekend Scout" in content


def test_format_message_no_events_graceful(tmp_path, monkeypatch):
    output = tmp_path / "msg.txt"
    result = _run_format_message(
        ["--saturday", "2026-03-28", "--sunday", "2026-03-29", "--output", str(output)],
        tmp_path, monkeypatch,
    )
    content = output.read_text(encoding="utf-8")
    assert "No events found" in content
    assert "No events found" in result["preview"]


def test_format_message_preview_is_plain_text(tmp_path, monkeypatch):
    output = tmp_path / "msg.txt"
    result = _run_format_message(
        ["--saturday", "2026-03-28", "--sunday", "2026-03-29", "--output", str(output)],
        tmp_path, monkeypatch,
    )
    assert "<b>" not in result["preview"]
    assert "<i>" not in result["preview"]
    assert "[<a href=" not in result["preview"]


# --- cmd_config: error handling ---

def test_cmd_config_set_int_invalid_value_returns_error(tmp_path, monkeypatch):
    result = _run_config(["radius_km", "not_a_number"], tmp_path, monkeypatch)
    assert "error" in result


def test_cmd_config_set_float_invalid_value_returns_error(tmp_path, monkeypatch):
    # home_coordinates is a dict, not float — test with a hypothetical float field
    # use radius_km coercion indirectly to confirm the error path
    result = _run_config(["radius_km", "3.5.9"], tmp_path, monkeypatch)
    assert "error" in result


def test_cmd_config_set_dict_value_parses_json(tmp_path, monkeypatch):
    result = _run_config(
        ["home_coordinates", '{"lat": 52.20, "lon": 20.91}'],
        tmp_path, monkeypatch,
    )
    assert result == {"set": {"home_coordinates": {"lat": 52.20, "lon": 20.91}}}
    # Verify the stored value is a dict, not a string
    stored = _run_config(["home_coordinates"], tmp_path, monkeypatch)
    assert isinstance(stored["home_coordinates"], dict)
    assert stored["home_coordinates"]["lat"] == 52.20


def test_cmd_config_set_dict_invalid_json_returns_error(tmp_path, monkeypatch):
    result = _run_config(["home_coordinates", "notjson"], tmp_path, monkeypatch)
    assert "error" in result


def test_cmd_config_set_dict_wrong_type_returns_error(tmp_path, monkeypatch):
    # home_coordinates expects a dict; passing a JSON list should fail
    result = _run_config(["home_coordinates", "[1, 2, 3]"], tmp_path, monkeypatch)
    assert "error" in result


# --- cmd_init ---

def _run_cmd(name: str, args: list[str], tmp_path, monkeypatch) -> str:
    """Helper: call any cmd_* function, return raw stdout capture (may be JSON string)."""
    import weekend_scout.config as cfg_module
    config_file = tmp_path / "config.yaml"
    monkeypatch.setattr(cfg_module, "get_config_path", lambda: config_file)
    monkeypatch.setattr(cfg_module, "get_config_dir", lambda: tmp_path)

    from weekend_scout.__main__ import build_parser, COMMANDS
    parser = build_parser()
    parsed = parser.parse_args([name] + args)

    captured = []
    monkeypatch.setattr("builtins.print", lambda *a, **kw: captured.append(str(a[0])))
    try:
        COMMANDS[name](parsed)
    except SystemExit:
        pass
    return captured[-1] if captured else ""


def _write_minimal_config(tmp_path) -> None:
    """Write a minimal valid config so cmd_init doesn't hit the needs_setup guard."""
    import yaml
    cfg = {
        "home_city": "Warsaw",
        "home_country": "Poland",
        "home_coordinates": {"lat": 52.2297, "lon": 21.0122},
        "radius_km": 150,
        "search_language": "pl",
    }
    (tmp_path / "config.yaml").write_text(yaml.dump(cfg), encoding="utf-8")


def _write_json_file(path: Path, payload, *, encoding: str = "utf-8") -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False), encoding=encoding)
    return path


def _write_skill_tmp_payload(tmp_path: Path, name: str, payload, *, encoding: str = "utf-8") -> Path:
    cache_dir = tmp_path / "cache"
    cache_dir.mkdir(parents=True, exist_ok=True)
    return _write_json_file(cache_dir / f"_tmp_{name}.tmp", payload, encoding=encoding)


def _write_action_log_fixture(tmp_path: Path, lines: list[dict]) -> Path:
    cache_dir = tmp_path / "cache"
    cache_dir.mkdir(parents=True, exist_ok=True)
    log_path = cache_dir / "action_log.jsonl"
    log_path.write_text(
        "\n".join(json.dumps(line, ensure_ascii=False) for line in lines) + "\n",
        encoding="utf-8",
    )
    return log_path


def _invoke_command_no_catch(name: str, args: list[str], tmp_path, monkeypatch):
    """Invoke one command directly and return (captured, raised_system_exit)."""
    import weekend_scout.config as cfg_module
    config_file = tmp_path / "config.yaml"
    monkeypatch.setattr(cfg_module, "get_config_path", lambda: config_file)
    monkeypatch.setattr(cfg_module, "get_config_dir", lambda: tmp_path)

    from weekend_scout.__main__ import build_parser, COMMANDS
    parser = build_parser()
    parsed = parser.parse_args([name] + args)

    captured = []
    monkeypatch.setattr("builtins.print", lambda *a, **kw: captured.append(str(a[0])))
    raised = None
    try:
        COMMANDS[name](parsed)
    except SystemExit as exc:
        raised = exc
    return captured[-1] if captured else "", raised


def test_cmd_init_radius_invalid_returns_error(tmp_path, monkeypatch):
    _write_minimal_config(tmp_path)
    output = _run_cmd("init", ["--radius", "abc"], tmp_path, monkeypatch)
    result = json.loads(output)
    assert "error" in result


def test_cmd_init_returns_json(tmp_path, monkeypatch):
    _write_minimal_config(tmp_path)
    # Patch get_city_list to avoid needing GeoNames file
    import weekend_scout.cities as cities_module
    monkeypatch.setattr(cities_module, "get_city_list",
                        lambda _cfg, bypass_cache=False: {"tier1": ["Potsdam|DE"], "tier2": [], "tier3": ["Szczecin|PL"]})
    output = _run_cmd("init", [], tmp_path, monkeypatch)
    result = json.loads(output)
    assert "config" in result
    assert "cities" in result
    assert "cached" in result
    assert "debug" in result
    assert "city_meta" not in result
    assert result["cities"] == {"tier1": ["Potsdam|DE"], "tier2_count": 0, "tier3_count": 1}
    sq = result["debug"]["suggested_queries"]
    assert "vars" in sq
    assert "broad" in sq
    assert "targeted_by_country" in sq
    assert "targeted_template" not in sq
    assert isinstance(sq["broad"], list)
    assert "{city}" in sq["targeted_by_country"]["DE"]["template"]
    assert sq["targeted_by_country"]["DE"]["date"]
    assert "{city}" in sq["targeted_by_country"]["PL"]["template"]
    assert sq["targeted_by_country"]["PL"]["date"]
    workflow = result["workflow"]
    assert workflow["coverage"]["minimum_home_city_events"] == 3
    assert workflow["phase_a"]["queries"]
    assert set(workflow["phase_a"]["queries"][0]) == {"query", "query_already_done"}
    assert workflow["phase_c"]["tier1"][0]["query"]
    assert set(workflow["phase_c"]["tier1"][0]) == {"city_name", "query", "query_already_done"}
    assert workflow["phase_d"]["max_candidates"] == 5
    assert result["cities"]["tier1"] == ["Potsdam|DE"]
    assert result["config"]["max_city_options"] == 3
    assert result["config"]["max_trip_options"] == 10
    assert result["config"]["max_searches"] == 30
    assert result["config"]["max_fetches"] == 30
    assert result["cached"] == {"count": 0, "covered_cities": [], "city_counts": {}}
    assert result["debug"]["cached_events"] == []
    assert result["debug"]["searches_this_week"] == []
    assert result["debug"]["cities_full"]["tier3"] == ["Szczecin|PL"]
    assert "minimum_trip_cities" not in workflow["coverage"]
    assert "tier1" not in result["debug"]["phase_c_full"]
    assert set(result["debug"]["phase_c_full"]["tier3"][0]) == {"city_name", "query", "query_already_done"}


def test_cmd_init_skill_returns_compact_cached_metadata(tmp_path, monkeypatch):
    _write_minimal_config(tmp_path)
    import weekend_scout.cities as cities_module
    monkeypatch.setattr(
        cities_module,
        "get_city_list",
        lambda _cfg, bypass_cache=False: {"tier1": ["Potsdam|DE"], "tier2": [], "tier3": ["Szczecin|PL"]},
    )
    output = _run_cmd("init-skill", [], tmp_path, monkeypatch)
    result = json.loads(output)
    assert "config" in result
    assert "cities" in result
    assert "cached" in result
    assert "cached_events" not in result
    assert "searches_this_week" not in result
    assert result["config"]["max_city_options"] == 3
    assert result["config"]["max_trip_options"] == 10
    assert result["cached"] == {"count": 0, "covered_cities": [], "city_counts": {}}
    assert "suggested_queries" not in result
    assert result["cities"] == {"tier1": ["Potsdam|DE"], "tier2_count": 0, "tier3_count": 1}
    workflow = result["workflow"]
    assert workflow["audit_command"].endswith(f'--run-id "{result["run_id"]}"')
    assert workflow["phase_a"]["search_limit"] == 5
    assert set(workflow["phase_a"]["queries"][0]) == {"query", "query_already_done"}
    assert workflow["phase_c"]["tier1"][0]["city_name"] == "Potsdam"
    assert set(workflow["phase_c"]["tier1"][0]) == {"city_name", "query", "query_already_done"}
    assert workflow["phase_c"]["tier2_request"]["available_count"] == 0
    assert workflow["phase_c"]["tier3_request"]["available_count"] == 1
    assert "phase_order" not in workflow
    assert "log_checkpoints" not in workflow
    assert "compact_note" in workflow
    assert "minimum_trip_cities" not in workflow["coverage"]


def test_cmd_init_skill_marks_done_queries_in_task_cards(tmp_path, monkeypatch):
    _write_minimal_config(tmp_path)
    import weekend_scout.cities as cities_module
    monkeypatch.setattr(
        cities_module,
        "get_city_list",
        lambda _cfg, bypass_cache=False: {"tier1": ["Potsdam|DE"], "tier2": [], "tier3": []},
    )
    first_result = json.loads(_run_cmd("init-skill", [], tmp_path, monkeypatch))
    query = first_result["workflow"]["phase_c"]["tier1"][0]["query"]
    _run_cmd(
        "log-search",
        ["--query", query, "--target-weekend", "2026-04-04",
         "--phase", "targeted", "--result-count", "1", "--cities", '["Potsdam"]'],
        tmp_path, monkeypatch,
    )
    output = _run_cmd("init-skill", [], tmp_path, monkeypatch)
    result = json.loads(output)
    tier1_card = result["workflow"]["phase_c"]["tier1"][0]
    assert tier1_card["query"] == query
    assert tier1_card["query_already_done"] is True


def test_cmd_init_skill_compact_payload_omits_full_later_tiers(tmp_path, monkeypatch):
    _write_minimal_config(tmp_path)
    import weekend_scout.cities as cities_module
    monkeypatch.setattr(
        cities_module,
        "get_city_list",
        lambda _cfg, bypass_cache=False: {
            "tier1": ["Potsdam|DE"],
            "tier2": ["Berlin|DE", "Brandenburg|DE"],
            "tier3": ["Szczecin|PL", "Lublin|PL"],
        },
    )
    result = json.loads(_run_cmd("init-skill", [], tmp_path, monkeypatch))
    assert result["cities"]["tier1"] == ["Potsdam|DE"]
    assert result["cities"]["tier2_count"] == 2
    assert result["cities"]["tier3_count"] == 2
    phase_c = result["workflow"]["phase_c"]
    assert "tier2" not in phase_c
    assert "tier3" not in phase_c
    assert phase_c["tier2_request"]["default_limit"] == 6
    assert phase_c["tier3_request"]["default_limit"] == 6


def test_cmd_init_skill_cached_summary_matches_saved_events(tmp_path, monkeypatch):
    _write_minimal_config(tmp_path)
    import weekend_scout.cities as cities_module
    monkeypatch.setattr(
        cities_module,
        "get_city_list",
        lambda _cfg, bypass_cache=False: {"tier1": ["Berlin|DE", "Potsdam|DE"], "tier2": [], "tier3": []},
    )
    _run_cmd(
        "save",
        ["--events", json.dumps([
            {"event_name": "A", "city": "Berlin", "start_date": "2026-04-04"},
            {"event_name": "B", "city": "Berlin", "start_date": "2026-04-05"},
            {"event_name": "C", "city": "Potsdam", "start_date": "2026-04-04"},
        ])],
        tmp_path,
        monkeypatch,
    )
    output = _run_cmd("init-skill", [], tmp_path, monkeypatch)
    result = json.loads(output)
    assert result["cached"]["count"] == 3
    assert result["cached"]["covered_cities"] == ["Berlin", "Potsdam"]
    assert result["cached"]["city_counts"] == {"Berlin": 2, "Potsdam": 1}


def test_cmd_init_skill_needs_setup_matches_init(tmp_path, monkeypatch):
    output = _run_cmd("init-skill", [], tmp_path, monkeypatch)
    result = json.loads(output)
    assert result["needs_setup"] is True


def test_cmd_init_skill_radius_invalid_returns_error(tmp_path, monkeypatch):
    _write_minimal_config(tmp_path)
    output = _run_cmd("init-skill", ["--radius", "abc"], tmp_path, monkeypatch)
    result = json.loads(output)
    assert "error" in result


# --- cmd_save ---

def test_cmd_save_returns_counts(tmp_path, monkeypatch):
    events = json.dumps([{
        "event_name": "Fest", "city": "Warsaw", "start_date": "2026-03-28",
    }])
    output = _run_cmd("save", ["--events", events], tmp_path, monkeypatch)
    result = json.loads(output)
    assert result == {"saved": 1, "skipped": 0}


def test_cmd_setup_accepts_json_file(tmp_path, monkeypatch):
    payload_path = _write_json_file(
        tmp_path / "setup.json",
        {
            "home_city": "Berlin",
            "home_country": "Germany",
            "home_coordinates": {"lat": 52.52437, "lon": 13.41053},
            "radius_km": 150,
        },
    )
    output = _run_cmd("setup", ["--json-file", str(payload_path)], tmp_path, monkeypatch)
    result = json.loads(output)
    assert result["saved"] is True

    stored = _run_config(["home_city"], tmp_path, monkeypatch)
    assert stored == {"home_city": "Berlin"}


def test_cmd_setup_derives_search_language_from_home_country(tmp_path, monkeypatch):
    payload_path = _write_json_file(
        tmp_path / "setup.json",
        {
            "home_city": "Berlin",
            "home_country": "Germany",
            "home_coordinates": {"lat": 52.52437, "lon": 13.41053},
            "radius_km": 150,
        },
    )
    output = _run_cmd("setup", ["--json-file", str(payload_path)], tmp_path, monkeypatch)
    result = json.loads(output)
    assert result["saved"] is True

    stored = _run_config(["search_language"], tmp_path, monkeypatch)
    assert stored == {"search_language": "de"}


def test_cmd_setup_keeps_explicit_search_language(tmp_path, monkeypatch):
    payload_path = _write_json_file(
        tmp_path / "setup.json",
        {
            "home_city": "Berlin",
            "home_country": "Germany",
            "home_coordinates": {"lat": 52.52437, "lon": 13.41053},
            "radius_km": 150,
            "search_language": "en",
        },
    )
    output = _run_cmd("setup", ["--json-file", str(payload_path)], tmp_path, monkeypatch)
    result = json.loads(output)
    assert result["saved"] is True

    stored = _run_config(["search_language"], tmp_path, monkeypatch)
    assert stored == {"search_language": "en"}


def test_cmd_setup_deletes_skill_generated_tmp_file_after_success(tmp_path, monkeypatch):
    payload_path = _write_skill_tmp_payload(
        tmp_path,
        "setup",
        {
            "home_city": "Berlin",
            "home_country": "Germany",
            "home_coordinates": {"lat": 52.52437, "lon": 13.41053},
        },
    )
    output = _run_cmd("setup", ["--json-file", str(payload_path)], tmp_path, monkeypatch)
    result = json.loads(output)
    assert result["saved"] is True
    assert not payload_path.exists()


def test_cmd_setup_json_file_accepts_utf8_bom(tmp_path, monkeypatch):
    payload_path = _write_json_file(
        tmp_path / "setup-bom.json",
        {
            "home_city": "Berlin",
            "home_country": "Germany",
            "home_coordinates": {"lat": 52.52437, "lon": 13.41053},
        },
        encoding="utf-8-sig",
    )
    output = _run_cmd("setup", ["--json-file", str(payload_path)], tmp_path, monkeypatch)
    result = json.loads(output)
    assert result["saved"] is True


def test_cmd_setup_json_file_missing_returns_error(tmp_path, monkeypatch):
    output = _run_cmd("setup", ["--json-file", str(tmp_path / "missing.json")], tmp_path, monkeypatch)
    result = json.loads(output)
    assert "error" in result
    assert "--json-file not found" in result["error"]


def test_cmd_setup_json_file_invalid_json_returns_error(tmp_path, monkeypatch):
    payload_path = tmp_path / "bad.json"
    payload_path.write_text("{bad", encoding="utf-8")
    output = _run_cmd("setup", ["--json-file", str(payload_path)], tmp_path, monkeypatch)
    result = json.loads(output)
    assert "error" in result
    assert "Invalid JSON in --json-file" in result["error"]


def test_cmd_setup_keeps_skill_tmp_file_when_json_invalid(tmp_path, monkeypatch):
    payload_path = tmp_path / "cache" / "_tmp_setup.tmp"
    payload_path.parent.mkdir(parents=True, exist_ok=True)
    payload_path.write_text("{bad", encoding="utf-8")
    output = _run_cmd("setup", ["--json-file", str(payload_path)], tmp_path, monkeypatch)
    result = json.loads(output)
    assert "error" in result
    assert payload_path.exists()


def test_cmd_setup_keeps_non_tmp_file_after_success(tmp_path, monkeypatch):
    payload_path = _write_json_file(
        tmp_path / "cache" / "setup.json",
        {
            "home_city": "Berlin",
            "home_country": "Germany",
            "home_coordinates": {"lat": 52.52437, "lon": 13.41053},
        },
    )
    output = _run_cmd("setup", ["--json-file", str(payload_path)], tmp_path, monkeypatch)
    result = json.loads(output)
    assert result["saved"] is True
    assert payload_path.exists()


def test_cmd_save_accepts_events_file(tmp_path, monkeypatch):
    payload_path = _write_skill_tmp_payload(
        tmp_path,
        "events",
        [{"event_name": "Fest", "city": "Warsaw", "start_date": "2026-03-28"}],
    )
    output = _run_cmd("save", ["--events-file", str(payload_path)], tmp_path, monkeypatch)
    result = json.loads(output)
    assert result == {"saved": 1, "skipped": 0}
    assert not payload_path.exists()


def test_cmd_save_events_file_missing_returns_error(tmp_path, monkeypatch):
    output = _run_cmd("save", ["--events-file", str(tmp_path / "missing.json")], tmp_path, monkeypatch)
    result = json.loads(output)
    assert "error" in result
    assert "--events-file not found" in result["error"]


# --- cmd_cache_query ---

def test_cmd_cache_query_returns_list(tmp_path, monkeypatch):
    output = _run_cmd("cache-query", ["--date", "2026-03-28"], tmp_path, monkeypatch)
    result = json.loads(output)
    assert isinstance(result, list)


# --- cmd_log_search ---

def test_cmd_log_search_returns_logged(tmp_path, monkeypatch):
    output = _run_cmd(
        "log-search",
        ["--query", "test query", "--target-weekend", "2026-03-28",
         "--phase", "broad", "--result-count", "5"],
        tmp_path, monkeypatch,
    )
    result = json.loads(output)
    assert result == {"logged": True}


def test_cmd_log_search_accepts_cities_file(tmp_path, monkeypatch):
    payload_path = _write_skill_tmp_payload(tmp_path, "cities", ["Berlin", "Potsdam"], encoding="utf-8-sig")
    output = _run_cmd(
        "log-search",
        ["--query", "test query", "--target-weekend", "2026-03-28",
         "--phase", "broad", "--result-count", "5", "--cities-file", str(payload_path)],
        tmp_path, monkeypatch,
    )
    result = json.loads(output)
    assert result == {"logged": True}
    assert not payload_path.exists()


def test_cmd_log_action_accepts_detail_file(tmp_path, monkeypatch):
    payload_path = _write_skill_tmp_payload(tmp_path, "detail", {"reason": "all_confirmed"}, encoding="utf-8-sig")
    output = _run_cmd(
        "log-action",
        ["--action", "skip", "--detail-file", str(payload_path)],
        tmp_path, monkeypatch,
    )
    result = json.loads(output)
    assert result == {"logged": True}
    assert not payload_path.exists()


def test_cmd_log_action_detail_file_invalid_json_returns_error(tmp_path, monkeypatch):
    payload_path = tmp_path / "detail.json"
    payload_path.write_text("{bad", encoding="utf-8")
    output = _run_cmd(
        "log-action",
        ["--action", "skip", "--detail-file", str(payload_path)],
        tmp_path, monkeypatch,
    )
    result = json.loads(output)
    assert "error" in result
    assert "Invalid JSON in --detail-file" in result["error"]


def test_cmd_phase_c_cities_batches_and_filters(tmp_path, monkeypatch):
    _write_minimal_config(tmp_path)
    import weekend_scout.cities as cities_module
    monkeypatch.setattr(
        cities_module,
        "get_city_list",
        lambda _cfg, bypass_cache=False: {
            "tier1": ["Potsdam|DE"],
            "tier2": ["Berlin|DE", "Brandenburg|DE", "Leipzig|DE", "Dresden|DE"],
            "tier3": [],
        },
    )
    initial = json.loads(
        _run_cmd(
            "phase-c-cities",
            ["--run-id", "2026-04-04_1200", "--tier", "2", "--offset", "0", "--limit", "4",
             "--covered-cities", "[]", "--searches-used", "0"],
            tmp_path, monkeypatch,
        )
    )
    done_query = initial["cards"][1]["query"]
    _run_cmd(
        "log-search",
        ["--query", done_query, "--target-weekend", "2026-04-04",
         "--phase", "targeted", "--cities", '["Brandenburg"]'],
        tmp_path, monkeypatch,
    )
    covered_path = _write_skill_tmp_payload(tmp_path, "covered", ["Berlin"])
    result = json.loads(
        _run_cmd(
            "phase-c-cities",
            ["--run-id", "2026-04-04_1200", "--tier", "2", "--offset", "0", "--limit", "2",
             "--covered-cities-file", str(covered_path), "--searches-used", "0"],
            tmp_path, monkeypatch,
        )
    )
    assert result["eligible"] is True
    assert [card["city_name"] for card in result["cards"]] == ["Leipzig", "Dresden"]
    assert result["available_count"] == 2
    assert result["has_more"] is False
    assert "budget_gate" not in result
    assert set(result["cards"][0]) == {"city_name", "query", "query_already_done"}
    assert not covered_path.exists()
    log_entries = (tmp_path / "cache" / "action_log.jsonl").read_text(encoding="utf-8").splitlines()
    last_entry = json.loads(log_entries[-1])
    assert last_entry["action"] == "phase_c_batch_requested"
    assert last_entry["detail"]["returned_count"] == 2


def test_cmd_phase_c_cities_logs_budget_blocked_request(tmp_path, monkeypatch):
    _write_minimal_config(tmp_path)
    import weekend_scout.cities as cities_module
    monkeypatch.setattr(
        cities_module,
        "get_city_list",
        lambda _cfg, bypass_cache=False: {"tier1": [], "tier2": ["Berlin|DE"], "tier3": []},
    )
    _run_cmd(
        "phase-c-cities",
        ["--run-id", "2026-04-04_1200", "--tier", "2", "--offset", "0", "--limit", "6",
         "--covered-cities", "[]", "--searches-used", "30"],
        tmp_path, monkeypatch,
    )
    log_entries = (tmp_path / "cache" / "action_log.jsonl").read_text(encoding="utf-8").splitlines()
    last_entry = json.loads(log_entries[-1])
    assert last_entry["action"] == "phase_c_batch_requested"
    assert last_entry["detail"]["eligible"] is False


def test_cmd_phase_c_cities_respects_budget_gate(tmp_path, monkeypatch):
    _write_minimal_config(tmp_path)
    import weekend_scout.cities as cities_module
    monkeypatch.setattr(
        cities_module,
        "get_city_list",
        lambda _cfg, bypass_cache=False: {"tier1": [], "tier2": ["Berlin|DE"], "tier3": []},
    )
    result = json.loads(
        _run_cmd(
            "phase-c-cities",
            ["--run-id", "2026-04-04_1200", "--tier", "2", "--offset", "0", "--limit", "6",
             "--covered-cities", "[]", "--searches-used", "30"],
            tmp_path, monkeypatch,
        )
    )
    assert result["eligible"] is False
    assert result["reason"] == "budget_gate_blocked"
    assert "budget_gate" not in result
    assert result["cards"] == []


def test_cmd_phase_summary_logs_canonical_counts(tmp_path, monkeypatch):
    _write_minimal_config(tmp_path)
    _write_action_log_fixture(
        tmp_path,
        [
            {"ts": "2026-04-03T12:24:45", "run_id": "run-a", "source": "python", "action": "run_init", "phase": None, "target_weekend": "2026-04-04", "detail": {"cached_count": 0, "tier1": ["Radom|PL"]}},
            {"ts": "2026-04-03T12:24:50", "run_id": "run-a", "source": "skill", "action": "phase_start", "phase": "A", "target_weekend": "2026-04-04", "detail": {}},
            {"ts": "2026-04-03T12:24:55", "run_id": "run-a", "source": "skill", "action": "search", "phase": "broad", "target_weekend": "2026-04-04", "detail": {"query": "q1", "result_count": 3, "cities": ["Warsaw"], "events_discovered": 1}},
            {"ts": "2026-04-03T12:25:00", "run_id": "run-a", "source": "skill", "action": "search", "phase": "broad", "target_weekend": "2026-04-04", "detail": {"query": "q2", "result_count": 2, "cities": ["Warsaw"], "events_discovered": 0}},
        ],
    )
    result = json.loads(
        _run_cmd(
            "phase-summary",
            ["--run-id", "run-a", "--phase", "A", "--target-weekend", "2026-04-04"],
            tmp_path, monkeypatch,
        )
    )
    assert result["logged"] is True
    assert result["detail"] == {
        "searches_used_in_phase": 2,
        "fetches_used_in_phase": 0,
        "new_events_in_phase": 1,
        "cumulative_searches_used": 2,
        "cumulative_fetches_used": 0,
    }


def test_cmd_phase_summary_rejects_duplicate_phase_summary(tmp_path, monkeypatch):
    _write_minimal_config(tmp_path)
    _write_action_log_fixture(
        tmp_path,
        [
            {"ts": "2026-04-03T12:24:45", "run_id": "run-a", "source": "python", "action": "run_init", "phase": None, "target_weekend": "2026-04-04", "detail": {"cached_count": 0, "tier1": ["Radom|PL"]}},
            {"ts": "2026-04-03T12:24:50", "run_id": "run-a", "source": "skill", "action": "phase_start", "phase": "A", "target_weekend": "2026-04-04", "detail": {}},
            {"ts": "2026-04-03T12:24:55", "run_id": "run-a", "source": "skill", "action": "phase_summary", "phase": "A", "target_weekend": "2026-04-04", "detail": {"searches_used_in_phase": 0, "fetches_used_in_phase": 0, "new_events_in_phase": 0, "cumulative_searches_used": 0, "cumulative_fetches_used": 0}},
        ],
    )
    result = json.loads(
        _run_cmd(
            "phase-summary",
            ["--run-id", "run-a", "--phase", "A", "--target-weekend", "2026-04-04"],
            tmp_path, monkeypatch,
        )
    )
    assert result["logged"] is False
    assert result["error"] == "phase already summarized"


def test_cleanup_transport_artifacts_removes_only_safe_patterns(tmp_path):
    from weekend_scout.__main__ import _cleanup_transport_artifacts

    cache_dir = tmp_path / "cache"
    cache_dir.mkdir()
    removable = [
        "setup.json",
        "events.json",
        "city-events.json",
        "trips.json",
        "covered-cities.json",
        "uncovered-tier1.json",
        "cities-1.json",
        "detail-a.json",
        "_tmp_test.tmp",
    ]
    keep = [
        "cache.db",
        "action_log.jsonl",
        "cities_Warsaw_100.json",
        "scout_message.txt",
    ]
    for name in removable + keep:
        (cache_dir / name).write_text("x", encoding="utf-8")

    removed = _cleanup_transport_artifacts(cache_dir)
    assert set(removed) == set(removable)
    for name in removable:
        assert not (cache_dir / name).exists()
    for name in keep:
        assert (cache_dir / name).exists()


def test_cmd_score_summary_logs_flat_payload(tmp_path, monkeypatch):
    _write_minimal_config(tmp_path)
    result = json.loads(
        _run_cmd(
            "score-summary",
            ["--run-id", "run-score", "--target-weekend", "2026-04-04",
             "--total-pool", "7", "--city-events-selected", "3", "--trip-options", "1"],
            tmp_path, monkeypatch,
        )
    )
    assert result["logged"] is True
    assert result["detail"] == {"total_pool": 7, "city_events_selected": 3, "trip_options": 1}


def test_cmd_run_complete_computes_counts_from_log(tmp_path, monkeypatch):
    _write_minimal_config(tmp_path)
    _write_action_log_fixture(
        tmp_path,
        [
            {"ts": "2026-04-03T12:24:45", "run_id": "run-complete", "source": "python", "action": "run_init", "phase": None, "target_weekend": "2026-04-04", "detail": {"cached_count": 2, "tier1": ["Radom|PL"]}},
            {"ts": "2026-04-03T12:24:50", "run_id": "run-complete", "source": "skill", "action": "search", "phase": "broad", "target_weekend": "2026-04-04", "detail": {"query": "q1", "result_count": 3, "cities": ["Warsaw"], "events_discovered": 1}},
            {"ts": "2026-04-03T12:25:00", "run_id": "run-complete", "source": "skill", "action": "fetch", "phase": "aggregator", "target_weekend": "2026-04-04", "detail": {"query": "u1", "result_count": 2, "cities": ["Warsaw"], "events_discovered": 2}},
            {"ts": "2026-04-03T12:25:10", "run_id": "run-complete", "source": "python", "action": "events_saved", "phase": None, "target_weekend": None, "detail": {"saved": 3, "skipped": 0}},
        ],
    )
    uncovered_path = _write_skill_tmp_payload(tmp_path, "uncovered", ["Radom"])
    result = json.loads(
        _run_cmd(
            "run-complete",
            ["--run-id", "run-complete", "--target-weekend", "2026-04-04",
             "--events-sent", "4", "--sent", "false",
             "--send-reason", "telegram_not_configured", "--served-marked", "false",
             "--uncovered-tier1-file", str(uncovered_path)],
            tmp_path, monkeypatch,
        )
    )
    assert result["logged"] is True
    assert result["detail"]["new_events"] == 3
    assert result["detail"]["searches_used"] == 1
    assert result["detail"]["fetches_used"] == 1
    assert result["detail"]["events_sent"] == 4
    assert result["detail"]["cached_events"] == 2
    assert not uncovered_path.exists()


def test_cmd_audit_run_flags_known_phase_drift(tmp_path, monkeypatch):
    _write_minimal_config(tmp_path)
    fixture_path = Path("tests/fixtures/phase_drift_2026-04-03.jsonl")
    _write_action_log_fixture(
        tmp_path,
        [json.loads(line) for line in fixture_path.read_text(encoding="utf-8").splitlines() if line.strip()],
    )
    result = json.loads(
        _run_cmd("audit-run", ["--run-id", "2026-04-04_1224"], tmp_path, monkeypatch)
    )
    assert result["ok"] is False
    assert any("Phase A" in error for error in result["errors"])
    assert any("phase_summary without a matching phase_start" in error for error in result["errors"])


def test_cmd_audit_run_default_is_advisory(tmp_path, monkeypatch):
    _write_minimal_config(tmp_path)
    fixture_path = Path("tests/fixtures/run_2026-04-03_1529.jsonl")
    _write_action_log_fixture(
        tmp_path,
        [json.loads(line) for line in fixture_path.read_text(encoding="utf-8").splitlines() if line.strip()],
    )
    _, raised = _invoke_command_no_catch(
        "audit-run", ["--run-id", "2026-04-04_1529"], tmp_path, monkeypatch
    )
    assert raised is None


def test_cmd_audit_run_strict_exits_non_zero(tmp_path, monkeypatch):
    _write_minimal_config(tmp_path)
    fixture_path = Path("tests/fixtures/run_2026-04-03_1529.jsonl")
    _write_action_log_fixture(
        tmp_path,
        [json.loads(line) for line in fixture_path.read_text(encoding="utf-8").splitlines() if line.strip()],
    )
    _, raised = _invoke_command_no_catch(
        "audit-run", ["--run-id", "2026-04-04_1529", "--strict"], tmp_path, monkeypatch
    )
    assert isinstance(raised, SystemExit)
    assert raised.code == 1


def test_cmd_audit_run_flags_score_summary_shape_on_last_failed_run(tmp_path, monkeypatch):
    _write_minimal_config(tmp_path)
    fixture_path = Path("tests/fixtures/run_2026-04-03_1529.jsonl")
    _write_action_log_fixture(
        tmp_path,
        [json.loads(line) for line in fixture_path.read_text(encoding="utf-8").splitlines() if line.strip()],
    )
    result = json.loads(
        _run_cmd("audit-run", ["--run-id", "2026-04-04_1529"], tmp_path, monkeypatch)
    )
    assert result["ok"] is False
    assert any("score_summary total_pool must be an integer" in error for error in result["errors"])


def test_cmd_audit_run_accepts_valid_run(tmp_path, monkeypatch):
    _write_minimal_config(tmp_path)
    _write_action_log_fixture(
        tmp_path,
        [
            {
                "ts": "2026-04-03T12:24:45",
                "run_id": "run-ok",
                "source": "python",
                "action": "run_init",
                "phase": None,
                "target_weekend": "2026-04-04",
                "detail": {"home_city": "Warsaw", "radius_km": 150, "cached_count": 0, "tier1": ["Radom|PL"]},
            },
            {
                "ts": "2026-04-03T12:24:50",
                "run_id": "run-ok",
                "source": "skill",
                "action": "phase_start",
                "phase": "A",
                "target_weekend": "2026-04-04",
                "detail": {},
            },
            {
                "ts": "2026-04-03T12:24:55",
                "run_id": "run-ok",
                "source": "skill",
                "action": "search",
                "phase": "broad",
                "target_weekend": "2026-04-04",
                "detail": {"query": "broad query", "result_count": 3, "cities": ["Warsaw"], "events_discovered": 1},
            },
            {
                "ts": "2026-04-03T12:25:00",
                "run_id": "run-ok",
                "source": "skill",
                "action": "phase_summary",
                "phase": "A",
                "target_weekend": "2026-04-04",
                "detail": {
                    "searches_used_in_phase": 1,
                    "fetches_used_in_phase": 0,
                    "new_events_in_phase": 1,
                    "cumulative_searches_used": 1,
                    "cumulative_fetches_used": 0,
                },
            },
            {
                "ts": "2026-04-03T12:25:05",
                "run_id": "run-ok",
                "source": "skill",
                "action": "skip",
                "phase": "B",
                "target_weekend": "2026-04-04",
                "detail": {"reason": "no_aggregator_urls"},
            },
            {
                "ts": "2026-04-03T12:25:10",
                "run_id": "run-ok",
                "source": "skill",
                "action": "skip",
                "phase": "C",
                "target_weekend": "2026-04-04",
                "detail": {"reason": "all_cities_covered"},
            },
            {
                "ts": "2026-04-03T12:25:15",
                "run_id": "run-ok",
                "source": "skill",
                "action": "skip",
                "phase": "D",
                "target_weekend": "2026-04-04",
                "detail": {"reason": "all_confirmed"},
            },
            {
                "ts": "2026-04-03T12:25:20",
                "run_id": "run-ok",
                "source": "python",
                "action": "events_saved",
                "phase": None,
                "target_weekend": None,
                "detail": {"saved": 1, "skipped": 0},
            },
            {
                "ts": "2026-04-03T12:25:25",
                "run_id": "run-ok",
                "source": "skill",
                "action": "score_summary",
                "phase": None,
                "target_weekend": "2026-04-04",
                "detail": {"total_pool": 1, "city_events_selected": 1, "trip_options": 0},
            },
            {
                "ts": "2026-04-03T12:25:30",
                "run_id": "run-ok",
                "source": "python",
                "action": "message_formatted",
                "phase": None,
                "target_weekend": "2026-04-04",
                "detail": {"city_events": 1, "trips": 0, "char_count": 250},
            },
            {
                "ts": "2026-04-03T12:25:35",
                "run_id": "run-ok",
                "source": "python",
                "action": "telegram_send",
                "phase": None,
                "target_weekend": None,
                "detail": {"success": True, "char_count": 250},
            },
            {
                "ts": "2026-04-03T12:25:40",
                "run_id": "run-ok",
                "source": "python",
                "action": "events_served",
                "phase": None,
                "target_weekend": "2026-04-04",
                "detail": {"count": 1},
            },
            {
                "ts": "2026-04-03T12:25:45",
                "run_id": "run-ok",
                "source": "skill",
                "action": "run_complete",
                "phase": None,
                "target_weekend": "2026-04-04",
                "detail": {
                    "events_sent": 1,
                    "new_events": 1,
                    "cached_events": 0,
                    "searches_used": 1,
                    "max_searches": 30,
                    "fetches_used": 0,
                    "max_fetches": 30,
                    "sent": True,
                    "send_reason": "sent",
                    "served_marked": True,
                    "uncovered_tier1": [],
                },
            },
        ],
    )
    result = json.loads(
        _run_cmd("audit-run", ["--run-id", "run-ok"], tmp_path, monkeypatch)
    )
    assert result["ok"] is True
    assert result["summary"]["searches_used"] == 1
    assert result["summary"]["completed_phases"] == ["A", "B", "C", "D"]


# --- cmd_cache_mark_served ---

def test_cmd_cache_mark_served_returns_count(tmp_path, monkeypatch):
    output = _run_cmd("cache-mark-served", ["--date", "2026-03-28"], tmp_path, monkeypatch)
    result = json.loads(output)
    assert "marked" in result


def test_format_message_logs_run_id(tmp_path, monkeypatch):
    output = tmp_path / "msg.txt"
    _run_format_message(
        ["--saturday", "2026-03-28", "--sunday", "2026-03-29",
         "--output", str(output), "--run-id", "run-xyz"],
        tmp_path, monkeypatch,
    )
    log_file = tmp_path / "cache" / "action_log.jsonl"
    entry = json.loads(log_file.read_text(encoding="utf-8").strip())
    assert entry["run_id"] == "run-xyz"
    assert entry["action"] == "message_formatted"


def test_format_message_accepts_json_files(tmp_path, monkeypatch):
    output = tmp_path / "msg.txt"
    city_events_path = _write_skill_tmp_payload(
        tmp_path,
        "city-events",
        [{"event_name": "Spring Festival", "city": "Warsaw", "start_date": "2026-03-28"}],
        encoding="utf-8-sig",
    )
    trips_path = _write_skill_tmp_payload(
        tmp_path,
        "trips",
        [{"name": "Berlin Day Trip", "route": "Berlin -> Potsdam -> Berlin", "events": "Market"}],
    )
    _run_format_message(
        ["--saturday", "2026-03-28", "--sunday", "2026-03-29",
         "--city-events-file", str(city_events_path), "--trips-file", str(trips_path),
         "--output", str(output)],
        tmp_path, monkeypatch,
    )
    content = output.read_text(encoding="utf-8")
    assert "Spring Festival" in content
    assert "Berlin Day Trip" in content
    assert not city_events_path.exists()
    assert not trips_path.exists()


def test_format_message_city_events_file_invalid_json_returns_error(tmp_path, monkeypatch):
    output = tmp_path / "msg.txt"
    payload_path = tmp_path / "bad-city-events.json"
    payload_path.write_text("{bad", encoding="utf-8")
    result = json.loads(
        _run_cmd(
            "format-message",
            ["--saturday", "2026-03-28", "--sunday", "2026-03-29",
             "--city-events-file", str(payload_path), "--output", str(output)],
            tmp_path, monkeypatch,
        )
    )
    assert "error" in result
    assert "Invalid JSON in --city-events-file" in result["error"]


def test_format_message_keeps_tmp_files_when_later_command_logic_fails(tmp_path, monkeypatch):
    import weekend_scout.telegram as telegram_module

    output = tmp_path / "msg.txt"
    city_events_path = _write_skill_tmp_payload(
        tmp_path,
        "city-events",
        [{"event_name": "Spring Festival", "city": "Warsaw", "start_date": "2026-03-28"}],
    )
    trips_path = _write_skill_tmp_payload(
        tmp_path,
        "trips",
        [{"name": "Berlin Day Trip", "route": "Berlin -> Potsdam -> Berlin", "events": "Market"}],
    )
    monkeypatch.setattr(telegram_module, "format_scout_message", lambda *a, **k: (_ for _ in ()).throw(RuntimeError("boom")))

    with pytest.raises(RuntimeError, match="boom"):
        _run_format_message(
            ["--saturday", "2026-03-28", "--sunday", "2026-03-29",
             "--city-events-file", str(city_events_path), "--trips-file", str(trips_path),
             "--output", str(output)],
            tmp_path, monkeypatch,
        )

    assert city_events_path.exists()
    assert trips_path.exists()


def test_format_message_mixed_cleanup_deletes_only_skill_tmp_files(tmp_path, monkeypatch):
    output = tmp_path / "msg.txt"
    city_events_path = _write_skill_tmp_payload(
        tmp_path,
        "city-events",
        [{"event_name": "Spring Festival", "city": "Warsaw", "start_date": "2026-03-28"}],
    )
    trips_path = _write_json_file(
        tmp_path / "cache" / "trips.json",
        [{"name": "Berlin Day Trip", "route": "Berlin -> Potsdam -> Berlin", "events": "Market"}],
    )
    _run_format_message(
        ["--saturday", "2026-03-28", "--sunday", "2026-03-29",
         "--city-events-file", str(city_events_path), "--trips-file", str(trips_path),
         "--output", str(output)],
        tmp_path, monkeypatch,
    )
    assert not city_events_path.exists()
    assert trips_path.exists()


# --- cmd_send ---

def test_cmd_send_missing_token_returns_sent_false(tmp_path, monkeypatch):
    msg_file = tmp_path / "msg.txt"
    msg_file.write_text("Hello", encoding="utf-8")
    output = _run_cmd("send", ["--file", str(msg_file)], tmp_path, monkeypatch)
    result = json.loads(output)
    assert result == {"sent": False}


def test_cmd_send_logs_run_id(tmp_path, monkeypatch):
    msg_file = tmp_path / "msg.txt"
    msg_file.write_text("Hello", encoding="utf-8")
    _run_cmd("send", ["--file", str(msg_file), "--run-id", "run-xyz"], tmp_path, monkeypatch)
    log_file = tmp_path / "cache" / "action_log.jsonl"
    entry = json.loads(log_file.read_text(encoding="utf-8").strip())
    assert entry["run_id"] == "run-xyz"
    assert entry["action"] == "telegram_send"


# --- cmd_run ---

def test_cmd_run_returns_json(tmp_path, monkeypatch):
    output = _run_cmd("run", [], tmp_path, monkeypatch)
    result = json.loads(output)
    assert "message" in result
