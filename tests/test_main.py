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
    assert result == {"written": str(output)}
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
    _run_format_message(
        ["--saturday", "2026-03-28", "--sunday", "2026-03-29", "--output", str(output)],
        tmp_path, monkeypatch,
    )
    content = output.read_text(encoding="utf-8")
    assert "No events found" in content


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


def test_cmd_init_radius_invalid_returns_error(tmp_path, monkeypatch):
    output = _run_cmd("init", ["--radius", "abc"], tmp_path, monkeypatch)
    result = json.loads(output)
    assert "error" in result


def test_cmd_init_returns_json(tmp_path, monkeypatch):
    # Patch get_city_list to avoid needing GeoNames file
    import weekend_scout.cities as cities_module
    monkeypatch.setattr(cities_module, "get_city_list",
                        lambda _cfg, bypass_cache=False: {"tier1": [], "tier2": [], "tier3": []})
    output = _run_cmd("init", [], tmp_path, monkeypatch)
    result = json.loads(output)
    assert "config" in result
    assert "cities" in result
    sq = result["suggested_queries"]
    assert "vars" in sq
    assert "broad" in sq
    assert "targeted_template" in sq
    assert "targeted" not in sq  # old format removed
    assert isinstance(sq["broad"], list)
    assert isinstance(sq["targeted_template"], str)
    assert "{city}" in sq["targeted_template"]


# --- cmd_save ---

def test_cmd_save_returns_counts(tmp_path, monkeypatch):
    events = json.dumps([{
        "event_name": "Fest", "city": "Warsaw", "start_date": "2026-03-28",
    }])
    output = _run_cmd("save", ["--events", events], tmp_path, monkeypatch)
    result = json.loads(output)
    assert result == {"saved": 1, "skipped": 0}


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


# --- cmd_cache_mark_served ---

def test_cmd_cache_mark_served_returns_count(tmp_path, monkeypatch):
    output = _run_cmd("cache-mark-served", ["--date", "2026-03-28"], tmp_path, monkeypatch)
    result = json.loads(output)
    assert "marked" in result


# --- cmd_send ---

def test_cmd_send_missing_token_returns_sent_false(tmp_path, monkeypatch):
    msg_file = tmp_path / "msg.txt"
    msg_file.write_text("Hello", encoding="utf-8")
    output = _run_cmd("send", ["--file", str(msg_file)], tmp_path, monkeypatch)
    result = json.loads(output)
    assert result == {"sent": False}


# --- cmd_run ---

def test_cmd_run_returns_json(tmp_path, monkeypatch):
    output = _run_cmd("run", [], tmp_path, monkeypatch)
    result = json.loads(output)
    assert "message" in result
