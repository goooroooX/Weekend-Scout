"""Tests for weekend_scout.config."""

import pytest
from pathlib import Path


@pytest.fixture
def patched_config_path(tmp_path, monkeypatch):
    """Redirect get_config_path to a temp file for isolation."""
    config_file = tmp_path / "config.yaml"
    import weekend_scout.config as cfg_module
    monkeypatch.setattr(cfg_module, "get_config_path", lambda: config_file)
    monkeypatch.setattr(cfg_module, "get_config_dir", lambda: tmp_path)
    return config_file


# --- get_config_path ---

def test_get_config_path_returns_path():
    from weekend_scout.config import get_config_path
    path = get_config_path()
    assert isinstance(path, Path)
    assert path.name == "config.yaml"


def test_get_config_path_is_inside_config_dir():
    from weekend_scout.config import get_config_path, get_config_dir
    assert get_config_path().parent == get_config_dir()


# --- load_config ---

def test_load_config_returns_defaults_when_no_file(patched_config_path):
    from weekend_scout.config import load_config
    result = load_config()
    assert result["home_city"] == ""
    assert result["radius_km"] == 150
    assert result["search_language"] == "en"
    assert isinstance(result["include_categories"], list)


def test_load_config_merges_with_defaults(patched_config_path, tmp_path):
    import yaml
    patched_config_path.write_text(
        yaml.dump({"home_city": "Krakow", "radius_km": 80}), encoding="utf-8"
    )
    from weekend_scout.config import load_config
    result = load_config()
    assert result["home_city"] == "Krakow"
    assert result["radius_km"] == 80
    # Default keys still present
    assert result["output_language"] == "en"
    assert result["max_trip_options"] == 3


def test_load_config_handles_empty_yaml(patched_config_path):
    patched_config_path.write_text("", encoding="utf-8")
    from weekend_scout.config import load_config
    result = load_config()
    assert result["radius_km"] == 150


# --- save_config / round-trip ---

def test_save_config_creates_file(patched_config_path):
    from weekend_scout.config import save_config
    save_config({"home_city": "Warsaw", "radius_km": 120})
    assert patched_config_path.exists()


def test_save_and_reload_config(patched_config_path):
    from weekend_scout.config import save_config, load_config
    save_config({"home_city": "Gdansk", "radius_km": 90})
    result = load_config()
    assert result["home_city"] == "Gdansk"
    assert result["radius_km"] == 90


def test_save_config_unicode(patched_config_path):
    from weekend_scout.config import save_config, load_config
    save_config({"home_city": "Łódź", "search_language": "pl"})
    result = load_config()
    assert result["home_city"] == "Łódź"


# --- get_cache_dir ---

def test_get_cache_dir_returns_path(patched_config_path, tmp_path):
    from weekend_scout.config import get_cache_dir, load_config
    config = load_config()
    cache_dir = get_cache_dir(config)
    assert isinstance(cache_dir, Path)
    assert cache_dir.exists()


def test_get_cache_dir_creates_directory(tmp_path, monkeypatch):
    import weekend_scout.config as cfg_module
    new_dir = tmp_path / "subdir"
    monkeypatch.setattr(cfg_module, "get_config_dir", lambda: new_dir)
    monkeypatch.setattr(cfg_module, "get_config_path", lambda: new_dir / "config.yaml")
    from weekend_scout.config import get_cache_dir
    result = get_cache_dir({})
    assert result.exists()


# --- run_setup_wizard ---

def test_run_setup_wizard_saves_config(patched_config_path, monkeypatch):
    inputs = iter([
        "Warsaw",       # home_city
        "Poland",       # home_country
        "52.2297",      # lat
        "21.0122",      # lon
        "150",          # radius_km
        "pl",           # search_language
        "",             # telegram token (skip)
        "",             # telegram chat_id (skip)
    ])
    monkeypatch.setattr("builtins.input", lambda _: next(inputs))
    from weekend_scout.config import run_setup_wizard
    result = run_setup_wizard()
    assert result["home_city"] == "Warsaw"
    assert result["search_language"] == "pl"
    assert patched_config_path.exists()


def test_run_setup_wizard_returns_dict(patched_config_path, monkeypatch):
    inputs = iter(["Krakow", "Poland", "50.06", "19.94", "120", "pl", "", ""])
    monkeypatch.setattr("builtins.input", lambda _: next(inputs))
    from weekend_scout.config import run_setup_wizard
    result = run_setup_wizard()
    assert isinstance(result, dict)
    assert result["home_city"] == "Krakow"
    assert result["radius_km"] == 120
    assert result["home_coordinates"] == {"lat": 50.06, "lon": 19.94}
