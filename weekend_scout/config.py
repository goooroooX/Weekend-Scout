"""Configuration management for Weekend Scout.

Handles reading, writing, and interactive setup of the YAML config file.
Config and cache files live in the platform-appropriate user config directory:
  - Linux/Mac: ~/.config/weekend-scout/
  - Windows:   %LOCALAPPDATA%\\weekend-scout\\weekend-scout\\
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml
from platformdirs import user_config_dir


APP_NAME = "weekend-scout"

# Country code -> search language
COUNTRY_LANGUAGE_MAP: dict[str, str] = {
    "Poland": "pl",
    "Germany": "de",
    "France": "fr",
    "Czech Republic": "cs",
    "Slovakia": "sk",
    "Austria": "de",
    "Hungary": "hu",
    "Ukraine": "uk",
    "Lithuania": "lt",
    "Latvia": "lv",
    "Estonia": "et",
    "Belarus": "be",
}

# ISO 3166-1 alpha-2 -> country name (matches COUNTRY_LANGUAGE_MAP keys)
COUNTRY_CODE_MAP: dict[str, str] = {
    "PL": "Poland",
    "DE": "Germany",
    "FR": "France",
    "CZ": "Czech Republic",
    "SK": "Slovakia",
    "AT": "Austria",
    "HU": "Hungary",
    "UA": "Ukraine",
    "LT": "Lithuania",
    "LV": "Latvia",
    "EE": "Estonia",
    "BY": "Belarus",
}

DEFAULT_CONFIG: dict[str, Any] = {
    "home_city": "",
    "home_country": "Poland",
    "home_coordinates": {"lat": 52.2297, "lon": 21.0122},
    "radius_km": 150,
    "search_language": "en",
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


def get_cache_dir(config: dict[str, Any]) -> Path:
    """Return the directory used for cache files (DB, city list JSON).

    Uses the same base directory as the config file. Creates it if needed.

    Args:
        config: Loaded configuration dictionary (unused currently, reserved
                for future per-profile cache directories).

    Returns:
        Path to the cache directory.
    """
    cache_dir = get_config_dir()
    cache_dir.mkdir(parents=True, exist_ok=True)
    return cache_dir


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


def _prompt(label: str, default: str = "") -> str:
    """Prompt the user for input, showing default in brackets."""
    suffix = f" [{default}]" if default else ""
    value = input(f"{label}{suffix}: ").strip()
    return value if value else default


def run_setup_wizard() -> dict[str, Any]:
    """Run interactive setup wizard to configure Weekend Scout.

    Prompts the user for required settings and saves them to disk.

    Returns:
        Completed configuration dictionary.
    """
    print("=== Weekend Scout Setup ===")
    print(f"Config will be saved to: {get_config_path()}\n")

    config = load_config()

    # Location
    config["home_city"] = _prompt("Home city", config.get("home_city") or "Warsaw")
    config["home_country"] = _prompt("Home country", config.get("home_country") or "Poland")

    # Coordinates
    print("\nHome city coordinates (used for distance calculations):")
    default_lat = str(config.get("home_coordinates", {}).get("lat", ""))
    default_lon = str(config.get("home_coordinates", {}).get("lon", ""))
    lat_str = _prompt("  Latitude", default_lat)
    lon_str = _prompt("  Longitude", default_lon)
    try:
        config["home_coordinates"] = {"lat": float(lat_str), "lon": float(lon_str)}
    except ValueError:
        print("  Invalid coordinates, keeping previous values.")

    # Search radius
    radius_str = _prompt("Search radius (km)", str(config.get("radius_km", 150)))
    try:
        config["radius_km"] = int(radius_str)
    except ValueError:
        print("  Invalid radius, keeping previous value.")

    # Search language (auto-derive from country, allow override)
    derived_lang = COUNTRY_LANGUAGE_MAP.get(config["home_country"], "en")
    config["search_language"] = _prompt("Search language (2-letter code)", derived_lang)

    # Telegram
    print("\nTelegram settings (leave blank to skip):")
    token = _prompt("  Bot token", config.get("telegram_bot_token") or "")
    if token:
        config["telegram_bot_token"] = token
    chat_id = _prompt("  Chat ID", config.get("telegram_chat_id") or "")
    if chat_id:
        config["telegram_chat_id"] = chat_id

    save_config(config)
    print(f"\nConfig saved to {get_config_path()}")
    return config
