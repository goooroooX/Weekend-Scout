"""Configuration management for Weekend Scout.

Handles reading, writing, and interactive setup of the YAML config file.
Config lives in the platform-appropriate user config directory:
  - Linux/Mac: ~/.config/weekend-scout/config.yaml
  - Windows:   %APPDATA%/weekend-scout/config.yaml
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml
from platformdirs import user_config_dir


APP_NAME = "weekend-scout"

DEFAULT_CONFIG: dict[str, Any] = {
    "home_city": "",
    "home_country": "Poland",
    "home_coordinates": {"lat": 52.2297, "lon": 21.0122},
    "precise_location": "",
    "radius_km": 150,
    "search_language": "pl",
    "include_categories": [
        "festival", "fair", "city_days", "reenactment",
        "street_art", "food_festival", "open_air_show",
    ],
    "exclude_categories": [
        "museum", "gallery", "theater", "cinema",
        "conference", "recurring_market",
    ],
    "max_city_options": 3,
    "max_trip_options": 3,
    "output_language": "en",
    "telegram_bot_token": "",
    "telegram_chat_id": "",
    "auto_run": False,
    "run_day": "friday",
    "run_time": "18:00",
}


def get_config_dir() -> Path:
    """Return the platform-appropriate config directory for Weekend Scout."""
    return Path(user_config_dir(APP_NAME))


def get_config_path() -> Path:
    """Return the full path to the config YAML file."""
    return get_config_dir() / "config.yaml"


def load_config() -> dict[str, Any]:
    """Load config from disk, returning defaults merged with stored values.

    Returns:
        Merged configuration dictionary.
    """
    path = get_config_path()
    if not path.exists():
        return dict(DEFAULT_CONFIG)
    with path.open("r", encoding="utf-8") as f:
        stored = yaml.safe_load(f) or {}
    merged = dict(DEFAULT_CONFIG)
    merged.update(stored)
    return merged


def save_config(config: dict[str, Any]) -> None:
    """Write config dictionary to disk.

    Args:
        config: Configuration dictionary to persist.
    """
    path = get_config_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        yaml.dump(config, f, allow_unicode=True, default_flow_style=False)


def run_setup_wizard() -> dict[str, Any]:
    """Run interactive setup wizard to configure Weekend Scout.

    Prompts the user for required settings and saves them to disk.

    Returns:
        Completed configuration dictionary.
    """
    pass


def get_cache_dir(config: dict[str, Any]) -> Path:
    """Return the directory used for cache files (DB, city list JSON).

    Args:
        config: Loaded configuration dictionary.

    Returns:
        Path to the cache directory (created if it does not exist).
    """
    pass
