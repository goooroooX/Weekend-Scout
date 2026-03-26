"""City list generation for Weekend Scout.

Loads city data from a GeoNames cities15000.txt file, filters by distance
from the home city, assigns search tiers, generates search queries, and
caches the result as a JSON file so repeated runs are fast.

Cache file: <cache_dir>/cities_<home_city>_<radius_km>.json
Invalidated when home_city or radius_km change.
"""

from __future__ import annotations

import datetime
import json
import zipfile
from pathlib import Path
from typing import Any

import requests

GEONAMES_ZIP_URL = "https://download.geonames.org/export/dump/cities15000.zip"
GEONAMES_FILENAME = "cities15000.txt"

# Month names for date localisation (Polish uses genitive forms)
MONTHS: dict[str, list[str]] = {
    "pl": [
        "stycznia", "lutego", "marca", "kwietnia", "maja", "czerwca",
        "lipca", "sierpnia", "września", "października", "listopada", "grudnia",
    ],
    "en": [
        "January", "February", "March", "April", "May", "June",
        "July", "August", "September", "October", "November", "December",
    ],
    "de": [
        "Januar", "Februar", "März", "April", "Mai", "Juni",
        "Juli", "August", "September", "Oktober", "November", "Dezember",
    ],
}

# Default data directory: <project_root>/data/
_DATA_DIR = Path(__file__).resolve().parent.parent / "data"


def download_geonames(force: bool = False) -> Path:
    """Download and unzip cities15000.zip from GeoNames into the data/ directory.

    Skips the download if data/cities15000.txt already exists, unless force=True.

    Args:
        force: Re-download even if the file is already present.

    Returns:
        Path to the extracted cities15000.txt file.
    """
    txt_path = _DATA_DIR / GEONAMES_FILENAME
    if txt_path.exists() and not force:
        return txt_path

    _DATA_DIR.mkdir(parents=True, exist_ok=True)
    zip_path = _DATA_DIR / "cities15000.zip"

    print(f"Downloading {GEONAMES_ZIP_URL} ...")
    response = requests.get(GEONAMES_ZIP_URL, stream=True, timeout=120)
    response.raise_for_status()
    with zip_path.open("wb") as f:
        for chunk in response.iter_content(chunk_size=65536):
            f.write(chunk)

    print("Extracting ...")
    with zipfile.ZipFile(zip_path) as zf:
        zf.extract(GEONAMES_FILENAME, _DATA_DIR)

    zip_path.unlink()
    print(f"Saved to {txt_path}")
    return txt_path


def parse_geonames_file(geonames_path: Path) -> list[dict[str, Any]]:
    """Parse a GeoNames cities15000.txt file into a list of city dicts.

    Tab-separated columns (GeoNames format, 19 columns):
      0  geonameid
      1  name           (native name / name_local)
      2  asciiname      (name, ASCII-safe)
      3  alternatenames
      4  latitude
      5  longitude
      6  feature_class
      7  feature_code
      8  country_code
      9  cc2
      10 admin1_code
      11 admin2_code
      12 admin3_code
      13 admin4_code
      14 population
      15 elevation
      16 dem
      17 timezone
      18 modification_date

    Args:
        geonames_path: Path to the cities15000.txt file.

    Returns:
        List of city dicts with keys:
          name, name_local, lat, lon, population, country.
    """
    cities: list[dict[str, Any]] = []
    with geonames_path.open("r", encoding="utf-8") as f:
        for line in f:
            cols = line.rstrip("\n").split("\t")
            if len(cols) < 19:
                continue
            try:
                cities.append({
                    "name": cols[2],         # asciiname
                    "name_local": cols[1],   # native name
                    "lat": float(cols[4]),
                    "lon": float(cols[5]),
                    "country": cols[8],
                    "population": int(cols[14]) if cols[14] else 0,
                })
            except ValueError:
                continue
    return cities


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
        Dict with keys 'tier1', 'tier2', 'tier3', each a list of city name strings
        (native/local names).
    """
    from weekend_scout.config import get_cache_dir
    from weekend_scout.distance import haversine_km

    home_city = config["home_city"]
    radius_km = config["radius_km"]
    cache_dir = get_cache_dir(config)
    cache_file = cache_dir / f"cities_{home_city}_{radius_km}.json"

    # Cache hit
    if cache_file.exists():
        data = json.loads(cache_file.read_text(encoding="utf-8"))
        result: dict[str, list[str]] = {"tier1": [], "tier2": [], "tier3": []}
        for city in data.get("cities", []):
            tier_key = f"tier{city['tier']}"
            if tier_key in result:
                result[tier_key].append(city["name_local"])
        return result

    # Cache miss — parse GeoNames file
    geonames_path = _DATA_DIR / GEONAMES_FILENAME
    if not geonames_path.exists():
        raise FileNotFoundError(
            f"GeoNames file not found at {geonames_path}. "
            "Run 'python -m weekend_scout download-data' first."
        )

    home_lat = config["home_coordinates"]["lat"]
    home_lon = config["home_coordinates"]["lon"]
    all_cities = parse_geonames_file(geonames_path)

    nearby: list[dict[str, Any]] = []
    for city in all_cities:
        dist = haversine_km(home_lat, home_lon, city["lat"], city["lon"])
        if dist < 2 or dist > radius_km:
            continue  # skip home city itself (< 2 km) and out-of-range cities
        city["distance_km"] = round(dist)
        city["tier"] = assign_tier(city["population"])
        nearby.append(city)

    nearby.sort(key=lambda c: c["distance_km"])

    # Write cache
    cache_data = {
        "generated": datetime.datetime.now().isoformat(),
        "home_city": home_city,
        "radius_km": radius_km,
        "country": config.get("home_country", ""),
        "cities": nearby,
    }
    cache_file.parent.mkdir(parents=True, exist_ok=True)
    cache_file.write_text(
        json.dumps(cache_data, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    result = {"tier1": [], "tier2": [], "tier3": []}
    for city in nearby:
        tier_key = f"tier{city['tier']}"
        if tier_key in result:
            result[tier_key].append(city["name_local"])
    return result


def get_region_name(home_city: str, regions_path: Path | None = None) -> str:
    """Look up the region name for a home city from data/regions.json.

    Args:
        home_city: City name (case-insensitive lookup).
        regions_path: Optional override path to regions.json.

    Returns:
        Region name string, or the home_city itself if not found.
    """
    if regions_path is None:
        regions_path = _DATA_DIR / "regions.json"
    try:
        data = json.loads(regions_path.read_text(encoding="utf-8"))
        lookup = {k.lower(): v for k, v in data.get("cities", {}).items()}
        return lookup.get(home_city.lower(), home_city)
    except (FileNotFoundError, json.JSONDecodeError):
        return home_city


def format_date_local(iso_date: str, lang: str) -> str:
    """Format an ISO date string in the given language for use in search queries.

    Supported languages: pl, en, de. Falls back to English for unknown codes.

    Examples:
        format_date_local('2026-03-28', 'pl') -> '28 marca 2026'
        format_date_local('2026-03-28', 'en') -> 'March 28, 2026'
        format_date_local('2026-03-28', 'de') -> '28. März 2026'

    Args:
        iso_date: Date string in 'YYYY-MM-DD' format.
        lang: Two-letter language code ('pl', 'en', 'de', etc.).

    Returns:
        Locale-formatted date string.
    """
    d = datetime.date.fromisoformat(iso_date)
    month_list = MONTHS.get(lang, MONTHS["en"])
    month_name = month_list[d.month - 1]

    if lang == "pl":
        return f"{d.day} {month_name} {d.year}"
    elif lang == "de":
        return f"{d.day}. {month_name} {d.year}"
    else:  # en and fallback
        return f"{month_name} {d.day}, {d.year}"


def generate_broad_queries(
    config: dict[str, Any], saturday: str, sunday: str
) -> list[str]:
    """Generate broad regional search queries for the target weekend.

    Produces 3 queries in the local language and 1 in English.

    Args:
        config: Loaded configuration dictionary.
        saturday: ISO date string of target Saturday.
        sunday: ISO date string of target Sunday.

    Returns:
        List of 4 search query strings.
    """
    lang = config.get("search_language", "pl")
    city = config.get("home_city", "")
    region = get_region_name(city)

    sat_str = format_date_local(saturday, lang)
    sat_date = datetime.date.fromisoformat(saturday)
    month_local = MONTHS.get(lang, MONTHS["en"])[sat_date.month - 1]
    en_sat = format_date_local(saturday, "en")

    return [
        f"imprezy plenerowe weekend {sat_str} {region}",
        f"festyny jarmarki okolice {city} {month_local} {sat_date.year}",
        f"wydarzenia plenerowe weekend {month_local} {sat_date.year} Polska",
        f"outdoor festivals events Poland {en_sat} {sat_date.year}",
    ]


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
    sat_str = format_date_local(saturday, lang)
    return {city: [f"{city} imprezy plenerowe {sat_str}"] for city in tier1_cities}
