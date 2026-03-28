"""Configuration management for Weekend Scout.

Handles reading, writing, and interactive setup of the YAML config file.
Config and cache files live in the platform-appropriate user config directory:
  - Linux/Mac: ~/.config/weekend-scout/
  - Windows:   %LOCALAPPDATA%\\weekend-scout\\
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
    "Italy": "it",
    "Spain": "es",
    "Portugal": "pt",
    "Netherlands": "nl",
    "Sweden": "sv",
    "Norway": "no",
    "Denmark": "da",
    "Finland": "fi",
    "Romania": "ro",
    "Croatia": "hr",
    "Bulgaria": "bg",
    "Serbia": "sr",
    "Greece": "el",
    "Turkey": "tr",
    "Russia": "ru",
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
    "IT": "Italy",
    "ES": "Spain",
    "PT": "Portugal",
    "NL": "Netherlands",
    "SE": "Sweden",
    "NO": "Norway",
    "DK": "Denmark",
    "FI": "Finland",
    "RO": "Romania",
    "HR": "Croatia",
    "BG": "Bulgaria",
    "RS": "Serbia",
    "GR": "Greece",
    "TR": "Turkey",
    "RU": "Russia",
}

DEFAULT_CONFIG: dict[str, Any] = {
    "home_city": "",
    "home_country": "",                               # populated during setup
    "home_coordinates": {"lat": 0.0, "lon": 0.0},   # 0,0 = unset sentinel
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
    import shutil
    new_dir = Path(user_config_dir(APP_NAME, appauthor=False))
    # One-time migration from the legacy double-nested path produced when appauthor
    # was not explicitly disabled (platformdirs used appname as author on Windows,
    # giving AppData\Local\weekend-scout\weekend-scout\ instead of AppData\Local\weekend-scout\).
    _legacy = new_dir / APP_NAME
    if _legacy.exists() and _legacy.is_dir():
        new_dir.mkdir(parents=True, exist_ok=True)
        for item in _legacy.iterdir():
            dest = new_dir / item.name
            if not dest.exists():
                shutil.move(str(item), str(dest))
        try:
            _legacy.rmdir()
        except OSError:
            pass  # leave in place if anything couldn't be moved
    return new_dir


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


def run_setup_wizard(_geonames_path: "Path | None" = None) -> dict[str, Any]:
    """Run interactive setup wizard to configure Weekend Scout.

    Asks only for city name and radius. Coordinates, country, and search
    language are resolved automatically from the GeoNames database.
    If the city is not found, the user is prompted for coordinates.

    Args:
        _geonames_path: Override GeoNames file path (used in tests).

    Returns:
        Completed configuration dictionary.
    """
    print("=== Weekend Scout Setup ===")
    print(f"Config will be saved to: {get_config_path()}\n")

    config = load_config()

    # -- City --
    while True:
        city = input("Home city: ").strip()
        if city:
            break
        print("  City name is required.")

    config["home_city"] = city

    # -- Auto-geocode from GeoNames --
    if _geonames_path is None:
        from weekend_scout.cities import _DATA_DIR, GEONAMES_FILENAME
        _geonames_path = _DATA_DIR / GEONAMES_FILENAME

    if _geonames_path.exists():
        from weekend_scout.cities import find_city_candidates
        candidates = find_city_candidates(city, _geonames_path)
        if len(candidates) == 1:
            c = candidates[0]
            print(f"  Found: {c['name']}, {c['country_name']} (pop. {c['population']:,})")
            config["home_city"] = c["name"]
            config["home_coordinates"] = {"lat": c["lat"], "lon": c["lon"]}
            config["home_country"] = c["country_name"]
            config["search_language"] = c["language"]
        elif len(candidates) > 1:
            print(f"  '{city}' found in multiple countries:")
            for i, c in enumerate(candidates, 1):
                print(f"    {i}. {c['name']}, {c['country_name']} (pop. {c['population']:,})")
            while True:
                choice = input("  Enter number [1]: ").strip() or "1"
                try:
                    idx = int(choice) - 1
                    if 0 <= idx < len(candidates):
                        c = candidates[idx]
                        config["home_city"] = c["name"]
                        config["home_coordinates"] = {"lat": c["lat"], "lon": c["lon"]}
                        config["home_country"] = c["country_name"]
                        config["search_language"] = c["language"]
                        break
                    print("  Invalid choice, try again.")
                except ValueError:
                    print("  Please enter a number.")
        else:
            print(f"  '{city}' not found in local database.")
            print("  Enter coordinates manually (or press Enter to skip):")
            lat_str = input("  Latitude: ").strip()
            lon_str = input("  Longitude: ").strip()
            if lat_str and lon_str:
                try:
                    config["home_coordinates"] = {"lat": float(lat_str), "lon": float(lon_str)}
                except ValueError:
                    print("  Invalid coordinates — skipping.")
            country = input("  Country name: ").strip()
            if country:
                config["home_country"] = country
                config["search_language"] = COUNTRY_LANGUAGE_MAP.get(country, "en")
    else:
        print("  Tip: Run 'python -m weekend_scout download-data' to enable nearby city suggestions.\n")

    # -- Radius --
    radius_str = input(f"Search radius in km [{config.get('radius_km', 150)}]: ").strip()
    if radius_str:
        try:
            config["radius_km"] = int(radius_str)
        except ValueError:
            print("  Invalid radius, keeping default.")

    # -- Telegram (optional) --
    print("\nTelegram settings (press Enter to skip — configure later with 'config' command):")
    token = input("  Bot token: ").strip()
    if token:
        config["telegram_bot_token"] = token
    chat_id = input("  Chat ID: ").strip()
    if chat_id:
        config["telegram_chat_id"] = chat_id

    save_config(config)
    print(f"\nConfig saved. Run /weekend-scout to start scouting!")
    return config
