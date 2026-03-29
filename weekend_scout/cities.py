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
import sys
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
    "fr": [
        "janvier", "février", "mars", "avril", "mai", "juin",
        "juillet", "août", "septembre", "octobre", "novembre", "décembre",
    ],
    "cs": [
        "ledna", "února", "března", "dubna", "května", "června",
        "července", "srpna", "září", "října", "listopadu", "prosince",
    ],
    "sk": [
        "januára", "februára", "marca", "apríla", "mája", "júna",
        "júla", "augusta", "septembra", "októbra", "novembra", "decembra",
    ],
    "hu": [
        "január", "február", "március", "április", "május", "június",
        "július", "augusztus", "szeptember", "október", "november", "december",
    ],
    "uk": [
        "січня", "лютого", "березня", "квітня", "травня", "червня",
        "липня", "серпня", "вересня", "жовтня", "листопада", "грудня",
    ],
    "lt": [
        "sausio", "vasario", "kovo", "balandžio", "gegužės", "birželio",
        "liepos", "rugpjūčio", "rugsėjo", "spalio", "lapkričio", "gruodžio",
    ],
    "lv": [
        "janvāris", "februāris", "marts", "aprīlis", "maijs", "jūnijs",
        "jūlijs", "augusts", "septembris", "oktobris", "novembris", "decembris",
    ],
    "et": [
        "jaanuar", "veebruar", "märts", "aprill", "mai", "juuni",
        "juuli", "august", "september", "oktoober", "november", "detsember",
    ],
    "be": [
        "студзеня", "лютага", "сакавіка", "красавіка", "мая", "чэрвеня",
        "ліпеня", "жніўня", "верасня", "кастрычніка", "лістапада", "снежня",
    ],
    "it": [
        "gennaio", "febbraio", "marzo", "aprile", "maggio", "giugno",
        "luglio", "agosto", "settembre", "ottobre", "novembre", "dicembre",
    ],
    "es": [
        "enero", "febrero", "marzo", "abril", "mayo", "junio",
        "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre",
    ],
    "pt": [
        "janeiro", "fevereiro", "março", "abril", "maio", "junho",
        "julho", "agosto", "setembro", "outubro", "novembro", "dezembro",
    ],
    "nl": [
        "januari", "februari", "maart", "april", "mei", "juni",
        "juli", "augustus", "september", "oktober", "november", "december",
    ],
    "sv": [
        "januari", "februari", "mars", "april", "maj", "juni",
        "juli", "augusti", "september", "oktober", "november", "december",
    ],
    "no": [
        "januar", "februar", "mars", "april", "mai", "juni",
        "juli", "august", "september", "oktober", "november", "desember",
    ],
    "da": [
        "januar", "februar", "marts", "april", "maj", "juni",
        "juli", "august", "september", "oktober", "november", "december",
    ],
    "fi": [
        "tammikuuta", "helmikuuta", "maaliskuuta", "huhtikuuta", "toukokuuta", "kesäkuuta",
        "heinäkuuta", "elokuuta", "syyskuuta", "lokakuuta", "marraskuuta", "joulukuuta",
    ],
    "ro": [
        "ianuarie", "februarie", "martie", "aprilie", "mai", "iunie",
        "iulie", "august", "septembrie", "octombrie", "noiembrie", "decembrie",
    ],
    "hr": [
        "siječnja", "veljače", "ožujka", "travnja", "svibnja", "lipnja",
        "srpnja", "kolovoza", "rujna", "listopada", "studenog", "prosinca",
    ],
    "bg": [
        "януари", "февруари", "март", "април", "май", "юни",
        "юли", "август", "септември", "октомври", "ноември", "декември",
    ],
    "sr": [
        "јануар", "фебруар", "март", "април", "мај", "јун",
        "јул", "август", "септембар", "октобар", "новембар", "децембар",
    ],
    "el": [
        "Ιανουαρίου", "Φεβρουαρίου", "Μαρτίου", "Απριλίου", "Μαΐου", "Ιουνίου",
        "Ιουλίου", "Αυγούστου", "Σεπτεμβρίου", "Οκτωβρίου", "Νοεμβρίου", "Δεκεμβρίου",
    ],
    "tr": [
        "Ocak", "Şubat", "Mart", "Nisan", "Mayıs", "Haziran",
        "Temmuz", "Ağustos", "Eylül", "Ekim", "Kasım", "Aralık",
    ],
    "ru": [
        "января", "февраля", "марта", "апреля", "мая", "июня",
        "июля", "августа", "сентября", "октября", "ноября", "декабря",
    ],
}

# Search query templates keyed by language code.
# Placeholders: {date}, {region}, {city}, {month}, {year}, {country}
# The English entry serves as the fallback for unknown languages.
QUERY_TEMPLATES: dict[str, dict[str, Any]] = {
    "pl": {
        "broad": [
            "imprezy plenerowe weekend {date} {region}",
            "festyny jarmarki okolice {city} {month} {year}",
            "wydarzenia plenerowe weekend {month} {year} {country}",
        ],
        "targeted": "{city} imprezy plenerowe {date}",
        "country": "Polska",
    },
    "de": {
        "broad": [
            "Veranstaltungen Freiluft Wochenende {date} {region}",
            "Feste Märkte Umgebung {city} {month} {year}",
            "Outdoor Events Wochenende {month} {year} {country}",
        ],
        "targeted": "{city} Veranstaltungen Freiluft {date}",
        "country": "Deutschland",
    },
    "fr": {
        "broad": [
            "événements plein air week-end {date} {region}",
            "festivals marchés environs {city} {month} {year}",
            "événements plein air week-end {month} {year} {country}",
        ],
        "targeted": "{city} événements plein air {date}",
        "country": "France",
    },
    "cs": {
        "broad": [
            "venkovní akce víkend {date} {region}",
            "festivaly jarmarky okolí {city} {month} {year}",
            "venkovní události víkend {month} {year} {country}",
        ],
        "targeted": "{city} venkovní akce {date}",
        "country": "Česko",
    },
    "sk": {
        "broad": [
            "vonkajšie podujatia víkend {date} {region}",
            "festivaly jarmoky okolie {city} {month} {year}",
            "vonkajšie udalosti víkend {month} {year} {country}",
        ],
        "targeted": "{city} vonkajšie podujatia {date}",
        "country": "Slovensko",
    },
    "hu": {
        "broad": [
            "szabadtéri rendezvények hétvége {date} {region}",
            "fesztiválok vásárok {city} környéke {month} {year}",
            "szabadtéri események hétvége {month} {year} {country}",
        ],
        "targeted": "{city} szabadtéri rendezvények {date}",
        "country": "Magyarország",
    },
    "uk": {
        "broad": [
            "заходи просто неба вихідні {date} {region}",
            "фестивалі ярмарки околиці {city} {month} {year}",
            "події просто неба вихідні {month} {year} {country}",
        ],
        "targeted": "{city} заходи просто неба {date}",
        "country": "Україна",
    },
    "lt": {
        "broad": [
            "lauko renginiai savaitgalis {date} {region}",
            "festivaliai mugės apylinkės {city} {month} {year}",
            "lauko renginiai savaitgalis {month} {year} {country}",
        ],
        "targeted": "{city} lauko renginiai {date}",
        "country": "Lietuva",
    },
    "lv": {
        "broad": [
            "āra pasākumi nedēļas nogale {date} {region}",
            "festivāli tirgi apkārtne {city} {month} {year}",
            "āra pasākumi nedēļas nogale {month} {year} {country}",
        ],
        "targeted": "{city} āra pasākumi {date}",
        "country": "Latvija",
    },
    "et": {
        "broad": [
            "vabaõhu üritused nädalavahetus {date} {region}",
            "festivalid laadad ümbrus {city} {month} {year}",
            "vabaõhu sündmused nädalavahetus {month} {year} {country}",
        ],
        "targeted": "{city} vabaõhu üritused {date}",
        "country": "Eesti",
    },
    "be": {
        "broad": [
            "мерапрыемствы на адкрытым паветры выхадныя {date} {region}",
            "фестывалі кірмашы ваколіцы {city} {month} {year}",
            "падзеі на адкрытым паветры выхадныя {month} {year} {country}",
        ],
        "targeted": "{city} мерапрыемствы на адкрытым паветры {date}",
        "country": "Беларусь",
    },
    "it": {
        "broad": [
            "eventi all'aperto weekend {date} {region}",
            "festival mercato sagra {city} {month} {year}",
            "manifestazioni all'aperto weekend {month} {year} {country}",
        ],
        "targeted": "eventi {city} {date}",
        "country": "Italia",
    },
    "es": {
        "broad": [
            "eventos al aire libre fin de semana {date} {region}",
            "festival mercado feria {city} {month} {year}",
            "actividades al aire libre fin de semana {month} {year} {country}",
        ],
        "targeted": "eventos {city} {date}",
        "country": "España",
    },
    "pt": {
        "broad": [
            "eventos ao ar livre fim de semana {date} {region}",
            "festival mercado feira {city} {month} {year}",
            "atividades ao ar livre fim de semana {month} {year} {country}",
        ],
        "targeted": "eventos {city} {date}",
        "country": "Portugal",
    },
    "nl": {
        "broad": [
            "buitenevenementen weekend {date} {region}",
            "festival markt kermis {city} {month} {year}",
            "buitenactiviteiten weekend {month} {year} {country}",
        ],
        "targeted": "evenementen {city} {date}",
        "country": "Nederland",
    },
    "sv": {
        "broad": [
            "utomhusevenemang helgen {date} {region}",
            "festival marknad {city} {month} {year}",
            "utomhusaktiviteter helgen {month} {year} {country}",
        ],
        "targeted": "evenemang {city} {date}",
        "country": "Sverige",
    },
    "no": {
        "broad": [
            "utendørsarrangementer helgen {date} {region}",
            "festival marked {city} {month} {year}",
            "utendørsaktiviteter helgen {month} {year} {country}",
        ],
        "targeted": "arrangementer {city} {date}",
        "country": "Norge",
    },
    "da": {
        "broad": [
            "udendørsbegivenheder weekend {date} {region}",
            "festival marked {city} {month} {year}",
            "udendørsaktiviteter weekend {month} {year} {country}",
        ],
        "targeted": "begivenheder {city} {date}",
        "country": "Danmark",
    },
    "fi": {
        "broad": [
            "ulkoilmatapahtumat viikonloppu {date} {region}",
            "festivaali tori {city} {month} {year}",
            "ulkoilmatapahtumat viikonloppu {month} {year} {country}",
        ],
        "targeted": "tapahtumat {city} {date}",
        "country": "Suomi",
    },
    "ro": {
        "broad": [
            "evenimente în aer liber weekend {date} {region}",
            "festival târg {city} {month} {year}",
            "activități în aer liber weekend {month} {year} {country}",
        ],
        "targeted": "evenimente {city} {date}",
        "country": "România",
    },
    "hr": {
        "broad": [
            "vanjski događaji vikend {date} {region}",
            "festival sajam {city} {month} {year}",
            "vanjske aktivnosti vikend {month} {year} {country}",
        ],
        "targeted": "događaji {city} {date}",
        "country": "Hrvatska",
    },
    "bg": {
        "broad": [
            "събития на открито уикенд {date} {region}",
            "фестивал пазар {city} {month} {year}",
            "открити мероприятия уикенд {month} {year} {country}",
        ],
        "targeted": "събития {city} {date}",
        "country": "България",
    },
    "sr": {
        "broad": [
            "događaji na otvorenom vikend {date} {region}",
            "festival sajam {city} {month} {year}",
            "aktivnosti na otvorenom vikend {month} {year} {country}",
        ],
        "targeted": "događaji {city} {date}",
        "country": "Srbija",
    },
    "el": {
        "broad": [
            "υπαίθριες εκδηλώσεις σαββατοκύριακο {date} {region}",
            "φεστιβάλ αγορά {city} {month} {year}",
            "υπαίθριες δραστηριότητες σαββατοκύριακο {month} {year} {country}",
        ],
        "targeted": "εκδηλώσεις {city} {date}",
        "country": "Ελλάδα",
    },
    "tr": {
        "broad": [
            "açık hava etkinlikleri hafta sonu {date} {region}",
            "festival pazar {city} {month} {year}",
            "açık hava aktiviteleri hafta sonu {month} {year} {country}",
        ],
        "targeted": "etkinlikler {city} {date}",
        "country": "Türkiye",
    },
    "ru": {
        "broad": [
            "мероприятия на открытом воздухе выходные {date} {region}",
            "фестиваль ярмарка {city} {month} {year}",
            "открытые мероприятия выходные {month} {year} {country}",
        ],
        "targeted": "мероприятия {city} {date}",
        "country": "Россия",
    },
    "en": {
        "broad": [
            "outdoor events weekend {date} {region}",
            "festivals fairs near {city} {month} {year}",
            "outdoor events weekend {month} {year} {country}",
        ],
        "targeted": "{city} outdoor events {date}",
        "country": "",  # filled from config["home_country"] at runtime
    },
}

def _geonames_dir() -> Path:
    """Return the directory for GeoNames data files."""
    from weekend_scout.config import get_config_dir
    d = get_config_dir() / "cache" / "geonames"
    d.mkdir(parents=True, exist_ok=True)
    return d

# Date format constants for format_date_local
_PERIOD_DAY_FIRST = {"de", "no", "da", "hr", "sr"}   # "DD. Month Year"
_DAY_FIRST = {                                          # "DD Month Year"
    "pl", "fr", "cs", "sk", "hu", "uk", "lt", "lv", "et", "be",
    "it", "es", "pt", "nl", "sv", "fi", "ro", "bg", "el", "tr", "ru",
}


def download_geonames(force: bool = False) -> Path:
    """Download and unzip cities15000.zip from GeoNames into the cache directory.

    Skips the download if cities15000.txt already exists, unless force=True.

    Args:
        force: Re-download even if the file is already present.

    Returns:
        Path to the extracted cities15000.txt file.
    """
    geonames_dir = _geonames_dir()
    txt_path = geonames_dir / GEONAMES_FILENAME
    if txt_path.exists() and not force:
        return txt_path

    zip_path = geonames_dir / "cities15000.zip"

    print(f"Downloading {GEONAMES_ZIP_URL} ...", file=sys.stderr)
    response = requests.get(GEONAMES_ZIP_URL, stream=True, timeout=120)
    response.raise_for_status()
    with zip_path.open("wb") as f:
        for chunk in response.iter_content(chunk_size=65536):
            f.write(chunk)

    print("Extracting ...", file=sys.stderr)
    with zipfile.ZipFile(zip_path) as zf:
        zf.extract(GEONAMES_FILENAME, geonames_dir)

    zip_path.unlink()
    print(f"Saved to {txt_path}", file=sys.stderr)
    return txt_path


def ensure_geonames(force: bool = False) -> Path:
    """Return path to cities15000.txt, downloading automatically if missing.

    Args:
        force: Re-download even if the file already exists.

    Returns:
        Path to the cities15000.txt file.
    """
    txt_path = _geonames_dir() / GEONAMES_FILENAME
    if not txt_path.exists() or force:
        print("GeoNames data not found — downloading automatically...", file=sys.stderr)
        download_geonames(force=force)
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
            if cols[7] == "PPLX":  # skip sections/districts of populated places
                continue
            try:
                cities.append({
                    "name": cols[2],         # asciiname
                    "name_local": cols[1],   # native name
                    "lat": float(cols[4]),
                    "lon": float(cols[5]),
                    "country": cols[8],
                    "population": int(cols[14]) if cols[14] else 0,
                    "feature_code": cols[7],
                    "admin2": cols[11],
                    "admin3": cols[12],
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


def get_city_list(config: dict[str, Any], bypass_cache: bool = False) -> dict[str, list[str]]:
    """Return cities within radius, grouped by tier, using cache when valid.

    Reads from cache if <cache_dir>/cities_<home>_<radius>.json exists,
    otherwise parses the GeoNames file and writes the cache.

    Args:
        config: Loaded configuration dictionary.
        bypass_cache: If True, skip the cache and recompute from GeoNames.
                      Use when home_coordinates may differ from a previous cache write
                      (e.g. when --city override geocoded new coordinates).

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
    if cache_file.exists() and not bypass_cache:
        data = json.loads(cache_file.read_text(encoding="utf-8"))
        result: dict[str, list[str]] = {"tier1": [], "tier2": [], "tier3": []}
        for city in data.get("cities", []):
            tier_key = f"tier{city['tier']}"
            if tier_key in result:
                result[tier_key].append(city["name_local"])
        return result

    # Cache miss — parse GeoNames file
    geonames_path = ensure_geonames()

    home_lat = config["home_coordinates"]["lat"]
    home_lon = config["home_coordinates"]["lon"]
    all_cities = parse_geonames_file(geonames_path)

    # Find the home city's GeoNames entry to get its admin codes.
    # Used to filter city districts that share admin codes with the home city
    # but are incorrectly tagged PPL instead of PPLX (affects Warsaw, Brussels, Madrid, etc.)
    home_candidates = [c for c in all_cities if haversine_km(home_lat, home_lon, c["lat"], c["lon"]) < 2]
    home_entry = min(home_candidates, key=lambda c: haversine_km(home_lat, home_lon, c["lat"], c["lon"]), default=None)
    home_admin2 = home_entry["admin2"] if home_entry else ""
    home_admin3 = home_entry["admin3"] if home_entry else ""

    nearby: list[dict[str, Any]] = []
    for city in all_cities:
        dist = haversine_km(home_lat, home_lon, city["lat"], city["lon"])
        if dist < 2 or dist > radius_km:
            continue  # skip home city itself and out-of-range cities
        # Skip districts: PPL entries sharing admin codes with home city, within 15 km.
        # These are city boroughs GeoNames incorrectly tags as standalone PPL
        # (known affected capitals: Warsaw, Brussels, Madrid, Paris, Dublin, Amsterdam, Stockholm).
        if (home_admin2
                and city["feature_code"] == "PPL"
                and dist < 15
                and city["admin2"] == home_admin2
                and city["admin3"] == home_admin3):
            continue
        city["distance_km"] = round(dist)
        city["tier"] = assign_tier(city["population"])
        nearby.append(city)

    nearby.sort(key=lambda c: c["distance_km"])

    # Write cache — strip internal-only fields not needed downstream
    _CACHE_FIELDS = {"name", "name_local", "lat", "lon", "country", "population", "distance_km", "tier"}
    nearby_for_cache = [{k: v for k, v in c.items() if k in _CACHE_FIELDS} for c in nearby]
    cache_data = {
        "generated": datetime.datetime.now().isoformat(),
        "home_city": home_city,
        "radius_km": radius_km,
        "country": config.get("home_country", ""),
        "cities": nearby_for_cache,
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
    """Look up the region name for a home city.

    Args:
        home_city: City name (case-insensitive lookup).
        regions_path: Deprecated, ignored. Kept for signature compatibility.

    Returns:
        Region name string, or the home_city itself if not found.
    """
    from weekend_scout.regions import REGIONS
    lower = home_city.lower()
    for k, v in REGIONS.items():
        if k.lower() == lower:
            return v
    return home_city


def format_date_local(iso_date: str, lang: str) -> str:
    """Format an ISO date string in the given language for use in search queries.

    Formats: "DD. Month Year" (de/no/da/hr/sr), "DD Month Year" (most European),
    "Month DD, Year" (en, fallback). Falls back to English for unknown codes.

    Examples:
        format_date_local('2026-03-28', 'pl') -> '28 marca 2026'
        format_date_local('2026-03-28', 'en') -> 'March 28, 2026'
        format_date_local('2026-03-28', 'de') -> '28. März 2026'
        format_date_local('2026-03-28', 'it') -> '28 marzo 2026'
        format_date_local('2026-03-28', 'no') -> '28. mars 2026'

    Args:
        iso_date: Date string in 'YYYY-MM-DD' format.
        lang: Two-letter language code ('pl', 'en', 'de', etc.).

    Returns:
        Locale-formatted date string.
    """
    d = datetime.date.fromisoformat(iso_date)
    month_list = MONTHS.get(lang, MONTHS["en"])
    month_name = month_list[d.month - 1]

    if lang in _PERIOD_DAY_FIRST:
        return f"{d.day}. {month_name} {d.year}"
    if lang in _DAY_FIRST:
        return f"{d.day} {month_name} {d.year}"
    return f"{month_name} {d.day}, {d.year}"  # en and unknown fallback


def find_city_candidates(
    city_name: str, geonames_path: Path, country_filter: str | None = None
) -> list[dict[str, Any]]:
    """Find cities matching a name in GeoNames, grouped by country.

    Returns one entry per country (highest-population match), sorted by
    population descending. Results are limited to supported countries
    (those present in COUNTRY_CODE_MAP).

    Args:
        city_name: City name to search (case-insensitive; checked against
                   both ASCII name and native name columns).
        geonames_path: Path to cities15000.txt.
        country_filter: Optional country name (full English name, case-insensitive)
                        to restrict results.

    Returns:
        List of dicts with keys: name, ascii_name, country_code, country_name,
        language, lat, lon, population.
    """
    from weekend_scout.config import COUNTRY_CODE_MAP, COUNTRY_LANGUAGE_MAP

    lower = city_name.lower()
    all_cities = parse_geonames_file(geonames_path)
    matches = [
        c for c in all_cities
        if c["name"].lower() == lower or (c["name_local"] and c["name_local"].lower() == lower)
    ]

    # Limit to supported countries
    supported = set(COUNTRY_CODE_MAP.keys())
    matches = [c for c in matches if c["country"] in supported]

    # Optional country filter
    if country_filter:
        cf_lower = country_filter.lower()
        filtered = [
            c for c in matches
            if COUNTRY_CODE_MAP.get(c["country"], "").lower() == cf_lower
        ]
        if filtered:
            matches = filtered

    # Deduplicate by country — keep highest-population entry per country
    by_country: dict[str, dict[str, Any]] = {}
    for c in matches:
        code = c["country"]
        if code not in by_country or c["population"] > by_country[code]["population"]:
            by_country[code] = c

    deduped = sorted(by_country.values(), key=lambda c: c["population"], reverse=True)

    return [
        {
            "name": c["name_local"] or c["name"],
            "ascii_name": c["name"],
            "country_code": c["country"],
            "country_name": COUNTRY_CODE_MAP.get(c["country"], c["country"]),
            "language": COUNTRY_LANGUAGE_MAP.get(
                COUNTRY_CODE_MAP.get(c["country"], ""), "en"
            ),
            "lat": c["lat"],
            "lon": c["lon"],
            "population": c["population"],
        }
        for c in deduped
    ]


def find_city_coords(city_name: str, geonames_path: Path) -> dict[str, Any] | None:
    """Find a city's coordinates by name in a GeoNames file.

    Returns the highest-population match for the given name, checking both
    the ASCII name and native name columns.

    Args:
        city_name: City name to search for (case-insensitive).
        geonames_path: Path to the cities15000.txt file.

    Returns:
        City dict with lat, lon, country, population keys, or None if not found.
    """
    lower = city_name.lower()
    all_cities = parse_geonames_file(geonames_path)
    matches = [
        c for c in all_cities
        if c["name"].lower() == lower or (c["name_local"] and c["name_local"].lower() == lower)
    ]
    if not matches:
        return None
    return max(matches, key=lambda c: c["population"])


def generate_broad_queries(
    config: dict[str, Any], saturday: str, sunday: str
) -> dict[str, Any]:
    """Generate broad regional search query templates for the target weekend.

    Returns raw templates with {placeholders} plus a vars dict the caller
    uses to fill them. Templates are not pre-filled so the skill can adapt
    them (e.g. substitute a different city discovered mid-search).

    Args:
        config: Loaded configuration dictionary.
        saturday: ISO date string of target Saturday.
        sunday: ISO date string of target Sunday (kept for signature compatibility).

    Returns:
        Dict with keys:
          "templates": list of 4 template strings (3 local-language + 1 English)
          "vars": substitution variables dict
    """
    lang = config.get("search_language", "en")
    city = config.get("home_city", "")
    region = get_region_name(city)

    sat_date = datetime.date.fromisoformat(saturday)
    date_local = format_date_local(saturday, lang)
    date_en = format_date_local(saturday, "en")
    month_local = MONTHS.get(lang, MONTHS["en"])[sat_date.month - 1]

    tmpl = QUERY_TEMPLATES.get(lang, QUERY_TEMPLATES["en"])
    country = tmpl["country"] or config.get("home_country", "")

    return {
        "templates": list(tmpl["broad"]) + ["outdoor festivals events {date_en}"],
        "vars": {
            "city": city,
            "region": region,
            "date": date_local,
            "month": month_local,
            "year": str(sat_date.year),
            "country": country,
            "date_en": date_en,
        },
    }


def generate_targeted_template(lang: str) -> str:
    """Return the targeted per-city query template for the given language.

    The template contains {city} and {date} placeholders. The caller fills
    them: ``template.format(city=city_name, date=vars["date"])``.

    Args:
        lang: Two-letter language code.

    Returns:
        Template string, e.g. "{city} imprezy plenerowe {date}".
    """
    return QUERY_TEMPLATES.get(lang, QUERY_TEMPLATES["en"])["targeted"]
