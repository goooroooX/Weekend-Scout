"""Tests for weekend_scout.config."""

import pytest
from pathlib import Path


@pytest.fixture
def tmp_config_dir(tmp_path, monkeypatch):
    """Override the config directory to a temp path for all config tests."""
    monkeypatch.setenv("HOME", str(tmp_path))
    return tmp_path


def test_get_config_path_returns_path():
    from weekend_scout.config import get_config_path
    path = get_config_path()
    assert isinstance(path, Path)
    assert path.name == "config.yaml"


def test_load_config_returns_defaults_when_no_file(tmp_config_dir, monkeypatch):
    from weekend_scout import config as cfg_module
    monkeypatch.setattr(cfg_module, "get_config_path", lambda: tmp_config_dir / "nonexistent.yaml")
    from weekend_scout.config import load_config
    result = load_config()
    assert "home_city" in result
    assert result["radius_km"] == 150


def test_save_and_reload_config(tmp_path, monkeypatch):
    from weekend_scout import config as cfg_module
    config_file = tmp_path / "config.yaml"
    monkeypatch.setattr(cfg_module, "get_config_path", lambda: config_file)
    from weekend_scout.config import save_config, load_config
    data = {"home_city": "Warsaw", "radius_km": 100}
    save_config(data)
    loaded = load_config()
    assert loaded["home_city"] == "Warsaw"
    assert loaded["radius_km"] == 100


def test_load_config_merges_with_defaults(tmp_path, monkeypatch):
    pass


def test_get_cache_dir_returns_path():
    pass


def test_run_setup_wizard():
    pass
