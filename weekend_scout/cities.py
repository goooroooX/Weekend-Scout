"""City list generation for Weekend Scout.

Loads city data from a GeoNames cities15000.txt file, filters by distance
from the home city, assigns search tiers, generates search queries, and
caches the result as a JSON file so repeated runs are fast.

Cache file: <cache_dir>/cities_<home_city>_<radius_km>.json
Invalidated when home_city or radius_km change.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

GEONAMES_ZIP_URL = "https://download.geonames.org/export/dump/cities15000.zip"
GEONAMES_FILENAME = "cities15000.txt"


def download_geonames(force: bool = False) -> Path:
    """Download and unzip cities15000.zip from GeoNames into the data/ directory.

    Skips the download if data/cities15000.txt already exists, unless force=True.

    Args:
        force: Re-download even if the file is already present.

    Returns:
        Path to the extracted cities15000.txt file.
    """
    pass


def parse_geonames_file(geonames_path: Path) -> list[dict[str, Any]]:
    """Parse a GeoNames cities15000.txt file into a list of city dicts.

    Expected tab-separated columns (GeoNames format):
      geonameid, name, asciiname, alternatenames, latitude, longitude,
      feature_class, feature_code, country_code, cc2, admin1_code,
      admin2_code, admin3_code, admin4_code, population, elevation,
      dem, timezone, modification_date

    Args:
        geonames_path: Path to the cities15000.txt file.

    Returns:
        List of city dicts with keys: name, lat, lon, population, country.
    """
    pass


def assign_tier(population: int) -> int:
    """Assign a search tier based on city population.

    Tier 1: 100,000+   (always search individually)
    Tier 2: 30,000-99,999 (cover via regional queries)
    Tier 3: 15,000-29,999 (regional queries only)

    Args:
        population: City population.

    Returns:
        Integer tier 1, 2, or 3.
    """
    if population >= 100_000:
        return 1
    elif population >= 30_000:
        return 2
    else:
        return 3


def get_city_list(config: dict[str, Any]) -> dict[str, list[str]]:
    """Return cities within radius, grouped by tier, using cache when valid.

    Reads from cache if <cache_dir>/cities_<home>_<radius>.json exists,
    otherwise parses the GeoNames file and writes the cache.

    Args:
        config: Loaded configuration dictionary.

    Returns:
        Dict with keys 'tier1', 'tier2', 'tier3', each a list of city name strings.
    """
    pass


def get_region_name(home_city: str, regions_path: Path | None = None) -> str:
    """Look up the region name for a home city from data/regions.json.

    Args:
        home_city: City name (case-insensitive lookup).
        regions_path: Optional override path to regions.json.

    Returns:
        Region name string, or the home_city itself if not found.
    """
    pass


def format_date_local(iso_date: str, lang: str) -> str:
    """Format an ISO date string in the given language for use in search queries.

    Example: format_date_local('2026-03-28', 'pl') -> '28 marca 2026'

    Args:
        iso_date: Date string in 'YYYY-MM-DD' format.
        lang: Two-letter language code ('pl', 'en', 'de', etc.).

    Returns:
        Locale-formatted date string.
    """
    pass


def generate_broad_queries(
    config: dict[str, Any], saturday: str, sunday: str
) -> list[str]:
    """Generate broad regional search queries for the target weekend.

    Args:
        config: Loaded configuration dictionary.
        saturday: ISO date string of target Saturday.
        sunday: ISO date string of target Sunday.

    Returns:
        List of search query strings (local language + 1 English).
    """
    pass


def generate_targeted_queries(
    tier1_cities: list[str], lang: str, saturday: str
) -> dict[str, list[str]]:
    """Generate targeted per-city search queries for Tier 1 cities.

    Args:
        tier1_cities: List of Tier 1 city names.
        lang: Two-letter language code.
        saturday: ISO date string of target Saturday.

    Returns:
        Dict mapping city name -> list of query strings.
    """
    pass
