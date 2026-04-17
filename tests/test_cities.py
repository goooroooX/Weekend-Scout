"""Tests for weekend_scout.cities."""

import json
import shutil
import zipfile
import pytest
from pathlib import Path


@pytest.fixture(autouse=True)
def _disable_country_alternate_name_downloads(monkeypatch):
    import weekend_scout.cities as cities_module

    monkeypatch.setattr(
        cities_module,
        "_download_zip",
        lambda _url, _zip_path: (_ for _ in ()).throw(
            RuntimeError("alternate-name download disabled in tests")
        ),
    )


def test_assign_tier_tier1():
    from weekend_scout.cities import assign_tier
    assert assign_tier(500_000) == 1
    assert assign_tier(100_000) == 1


def test_assign_tier_tier2():
    from weekend_scout.cities import assign_tier
    assert assign_tier(50_000) == 2
    assert assign_tier(30_000) == 2


def test_assign_tier_tier3():
    from weekend_scout.cities import assign_tier
    assert assign_tier(20_000) == 3
    assert assign_tier(15_000) == 3


def test_get_region_name_known_city():
    from weekend_scout.cities import get_region_name
    assert get_region_name("Warsaw") == "Mazowsze"
    assert get_region_name("Krakow") == "Malopolska"


def test_get_region_name_case_insensitive():
    from weekend_scout.cities import get_region_name
    assert get_region_name("warsaw") == "Mazowsze"
    assert get_region_name("WARSAW") == "Mazowsze"


def test_get_region_name_unknown_city_returns_city():
    from weekend_scout.cities import get_region_name
    assert get_region_name("Atlantis") == "Atlantis"


def test_get_region_name_from_regions_module():
    from weekend_scout.cities import get_region_name
    # Verifies that get_region_name() reads from regions.py (not JSON)
    assert get_region_name("Berlin") == "Brandenburg"
    assert get_region_name("Paris") == "Île-de-France"


def test_format_date_local_polish():
    from weekend_scout.cities import format_date_local
    assert format_date_local("2026-03-28", "pl") == "28 marca 2026"
    assert format_date_local("2026-12-01", "pl") == "1 grudnia 2026"


def test_format_date_local_english():
    from weekend_scout.cities import format_date_local
    assert format_date_local("2026-03-28", "en") == "March 28, 2026"
    assert format_date_local("2026-01-05", "en") == "January 5, 2026"


def test_format_date_local_japanese():
    from weekend_scout.cities import format_date_local
    assert format_date_local("2026-04-10", "ja") == "2026年4月10日"


def test_format_date_local_korean():
    from weekend_scout.cities import format_date_local
    assert format_date_local("2026-04-10", "ko") == "2026년 4월 10일"


def test_format_date_local_german():
    from weekend_scout.cities import format_date_local
    assert format_date_local("2026-03-28", "de") == "28. März 2026"


def test_format_date_local_unknown_lang_falls_back_to_english():
    from weekend_scout.cities import format_date_local
    result = format_date_local("2026-03-28", "xx")
    assert "March" in result
    assert "2026" in result


def test_format_date_local_italian():
    from weekend_scout.cities import format_date_local
    assert format_date_local("2026-04-10", "it") == "10 aprile 2026"


def test_format_date_local_norwegian():
    from weekend_scout.cities import format_date_local
    assert format_date_local("2026-04-10", "no") == "10. april 2026"


def test_format_date_local_russian():
    from weekend_scout.cities import format_date_local
    assert format_date_local("2026-04-10", "ru") == "10 апреля 2026"


def test_normalize_city_input_strips_parenthesized_country():
    from weekend_scout.cities import normalize_city_input

    city, country = normalize_city_input("new york (usa)")

    assert city == "New York"
    assert country == "United States"


def test_normalize_city_input_strips_comma_country():
    from weekend_scout.cities import normalize_city_input

    city, country = normalize_city_input("warsaw, poland")

    assert city == "Warsaw"
    assert country == "Poland"


def test_normalize_city_input_keeps_clean_name():
    from weekend_scout.cities import normalize_city_input

    city, country = normalize_city_input("Łódź")

    assert city == "Łódź"
    assert country is None


def _make_geonames_row(
    geonameid="1234", name="Łódź", asciiname="Lodz",
    lat="51.7592", lon="19.4560", country="PL", population="672185",
    feature_code="PPLA", admin2="", admin3="", alternate_names="",
) -> str:
    cols = [
        geonameid, name, asciiname, alternate_names,   # 0-3
        lat, lon,                          # 4-5
        "P", feature_code,                 # 6-7
        country, "",                       # 8-9
        "", admin2, admin3, "",            # 10-13
        population, "", "100",             # 14-16
        "Europe/Warsaw", "2024-01-01",     # 17-18
    ]
    return "\t".join(cols)


def _make_alternate_name_row(
    alternate_name_id: str,
    geonameid: str,
    isolanguage: str,
    name: str,
    *,
    is_preferred: bool = False,
    is_short: bool = False,
    is_colloquial: bool = False,
    is_historic: bool = False,
) -> str:
    return "\t".join(
        [
            alternate_name_id,
            geonameid,
            isolanguage,
            name,
            "1" if is_preferred else "",
            "1" if is_short else "",
            "1" if is_colloquial else "",
            "1" if is_historic else "",
            "",
            "",
        ]
    )


def _write_fake_country_alternate_zip(tmp_path: Path, country_code: str, files: dict[str, str]) -> Path:
    source_dir = tmp_path / "zip_source"
    source_dir.mkdir(exist_ok=True)
    zip_path = source_dir / f"{country_code}.zip"
    with zipfile.ZipFile(zip_path, "w") as zf:
        for name, content in files.items():
            zf.writestr(name, content)
    return zip_path


def test_parse_geonames_file(tmp_path):
    from weekend_scout.cities import parse_geonames_file
    content = "\n".join([
        _make_geonames_row("1", "Łódź", "Lodz", "51.7592", "19.4560", "PL", "672185"),
        _make_geonames_row("2", "Radom", "Radom", "51.4027", "21.1471", "PL", "210532"),
    ])
    p = tmp_path / "cities.txt"
    p.write_text(content, encoding="utf-8")
    cities = parse_geonames_file(p)
    assert len(cities) == 2
    assert cities[0]["name"] == "Lodz"
    assert cities[0]["name_local"] == "Łódź"
    assert cities[0]["lat"] == pytest.approx(51.7592)
    assert cities[0]["country"] == "PL"
    assert cities[0]["population"] == 672185


def test_parse_geonames_file_skips_short_rows(tmp_path):
    from weekend_scout.cities import parse_geonames_file
    p = tmp_path / "cities.txt"
    p.write_text("only\ta\tfew\tcols\n" + _make_geonames_row(), encoding="utf-8")
    cities = parse_geonames_file(p)
    assert len(cities) == 1  # short row skipped


def _make_pplx_row(name="Wola", asciiname="Wola") -> str:
    """Return a GeoNames row with feature_code PPLX (section of populated place)."""
    return _make_geonames_row(
        geonameid="9999", name=name, asciiname=asciiname,
        lat="52.23", lon="20.98", country="PL", population="150000",
        feature_code="PPLX",
    )


def test_parse_geonames_file_skips_pplx(tmp_path):
    from weekend_scout.cities import parse_geonames_file
    content = "\n".join([
        _make_geonames_row("1", "Warsaw", "Warsaw", "52.23", "21.01", "PL", "1700000"),
        _make_pplx_row("Wola", "Wola"),    # district — should be skipped
        _make_pplx_row("Mokotow", "Mokotow"),  # district — should be skipped
    ])
    p = tmp_path / "cities.txt"
    p.write_text(content, encoding="utf-8")
    cities = parse_geonames_file(p)
    assert len(cities) == 1
    assert cities[0]["name"] == "Warsaw"


def test_get_city_list_filters_home_districts(tmp_path, monkeypatch):
    """PPL entries sharing admin codes with home city should be excluded (Warsaw/Brussels pattern)."""
    import weekend_scout.config as cfg_module
    import weekend_scout.cities as cities_module
    from weekend_scout.cities import get_city_list

    monkeypatch.setattr(cfg_module, "get_cache_dir", lambda _config: tmp_path)
    monkeypatch.setattr(cities_module, "_geonames_dir", lambda: tmp_path)

    # Home city: Warsaw-like PPLC at (52.23, 21.01), adm2=1465, adm3=146501
    home_row = _make_geonames_row(
        "1", "Warsaw", "Warsaw", "52.23", "21.01", "PL", "1700000",
        feature_code="PPLC", admin2="1465", admin3="146501",
    )
    # District: PPL at 5 km, same admin codes — should be filtered
    district_row = _make_geonames_row(
        "2", "Wola", "Wola", "52.27", "20.98", "PL", "140000",
        feature_code="PPL", admin2="1465", admin3="146501",
    )
    # Real nearby city: PPLA2, different admin codes, 20 km away — should be included
    real_city_row = _make_geonames_row(
        "3", "Pruszkow", "Pruszkow", "52.17", "20.80", "PL", "55000",
        feature_code="PPLA2", admin2="1421", admin3="142102",
    )

    geonames_file = tmp_path / "cities15000.txt"
    geonames_file.write_text("\n".join([home_row, district_row, real_city_row]), encoding="utf-8")

    config = {
        "home_city": "Warsaw",
        "radius_km": 150,
        "home_coordinates": {"lat": 52.23, "lon": 21.01},
        "home_country": "Poland",
    }
    result = get_city_list(config)

    all_names = result["tier1"] + result["tier2"] + result["tier3"]
    assert "Wola|PL" not in all_names       # district filtered
    assert "Pruszkow|PL" in all_names       # real city kept


def test_get_city_list_includes_country_code_suffix_for_cross_border_cities(tmp_path, monkeypatch):
    import weekend_scout.config as cfg_module
    import weekend_scout.cities as cities_module
    from weekend_scout.cities import get_city_list

    monkeypatch.setattr(cfg_module, "get_cache_dir", lambda _config: tmp_path)
    monkeypatch.setattr(cities_module, "_geonames_dir", lambda: tmp_path)

    home_row = _make_geonames_row(
        "1", "Berlin", "Berlin", "52.52", "13.40", "DE", "3500000",
        feature_code="PPLC", admin2="11000", admin3="110000",
    )
    potsdam_row = _make_geonames_row(
        "2", "Potsdam", "Potsdam", "52.40", "13.06", "DE", "187000",
        feature_code="PPLA", admin2="12054", admin3="12054000",
    )
    szczecin_row = _make_geonames_row(
        "3", "Szczecin", "Szczecin", "53.43", "14.55", "PL", "396000",
        feature_code="PPLA", admin2="3262", admin3="326201",
    )

    geonames_file = tmp_path / "cities15000.txt"
    geonames_file.write_text("\n".join([home_row, potsdam_row, szczecin_row]), encoding="utf-8")

    config = {
        "home_city": "Berlin",
        "radius_km": 150,
        "home_coordinates": {"lat": 52.52, "lon": 13.40},
        "home_country": "Germany",
    }
    result = get_city_list(config)

    all_names = result["tier1"] + result["tier2"] + result["tier3"]
    assert "Potsdam|DE" in all_names
    assert "Szczecin|PL" in all_names


def test_generate_broad_queries_returns_dict():
    from weekend_scout.cities import generate_broad_queries
    config = {
        "home_city": "Warsaw",
        "search_language": "pl",
        "home_country": "Poland",
    }
    result = generate_broad_queries(config, "2026-03-28", "2026-03-29")
    assert isinstance(result, dict)
    assert "templates" in result
    assert "vars" in result
    assert len(result["templates"]) == 4
    assert any("Mazowsze" in t or "{region}" in t for t in result["templates"])
    assert any("outdoor" in t.lower() for t in result["templates"])


def test_generate_broad_queries_vars_contain_date():
    from weekend_scout.cities import generate_broad_queries
    config = {"home_city": "Warsaw", "search_language": "pl", "home_country": "Poland"}
    result = generate_broad_queries(config, "2026-03-28", "2026-03-29")
    assert "marca" in result["vars"]["date"]    # Polish month in vars
    assert "March" in result["vars"]["date_en"] # English date in vars
    assert result["vars"]["city"] == "Warsaw"
    assert result["vars"]["year"] == "2026"


def test_generate_broad_queries_templates_are_unfilled():
    from weekend_scout.cities import generate_broad_queries
    config = {"home_city": "Warsaw", "search_language": "pl", "home_country": "Poland"}
    result = generate_broad_queries(config, "2026-03-28", "2026-03-29")
    # Templates should contain at least one {placeholder}
    assert any("{" in t for t in result["templates"])


def test_generate_broad_queries_templates_fill_correctly():
    from weekend_scout.cities import generate_broad_queries
    config = {"home_city": "Warsaw", "search_language": "pl", "home_country": "Poland"}
    result = generate_broad_queries(config, "2026-03-28", "2026-03-29")
    filled = [t.format(**result["vars"]) for t in result["templates"]]
    combined = " ".join(filled)
    assert "marca" in combined    # Polish month
    assert "March" in combined    # English fallback
    assert "outdoor events weekend March 28, 2026 Polska" in combined
    assert "imprezy" in combined  # Polish keyword


def test_generate_broad_queries_german():
    from weekend_scout.cities import generate_broad_queries
    config = {"home_city": "Berlin", "search_language": "de", "home_country": "Germany"}
    result = generate_broad_queries(config, "2026-03-28", "2026-03-29")
    filled = [t.format(**result["vars"]) for t in result["templates"]]
    combined = " ".join(filled)
    assert len(result["templates"]) == 4
    assert "Veranstaltungen" in combined or "Freiluft" in combined
    assert "imprezy" not in combined    # no Polish
    assert "März" in result["vars"]["date"]    # German month in vars
    assert "March" in result["vars"]["date_en"]  # English fallback still present


def test_generate_broad_queries_french():
    from weekend_scout.cities import generate_broad_queries
    config = {"home_city": "Paris", "search_language": "fr", "home_country": "France"}
    result = generate_broad_queries(config, "2026-03-28", "2026-03-29")
    filled = [t.format(**result["vars"]) for t in result["templates"]]
    combined = " ".join(filled)
    assert "événements" in combined or "plein air" in combined
    assert "imprezy" not in combined
    assert "March" in result["vars"]["date_en"]


def test_generate_broad_queries_italian():
    from weekend_scout.cities import generate_broad_queries
    config = {"home_city": "Rome", "search_language": "it", "home_country": "Italy"}
    result = generate_broad_queries(config, "2026-04-04", "2026-04-05")
    filled = [t.format(**result["vars"]) for t in result["templates"]]
    combined = " ".join(filled)
    assert "eventi" in combined
    assert "aprile" in result["vars"]["date"]
    assert "imprezy" not in combined


def test_generate_broad_queries_spanish():
    from weekend_scout.cities import generate_broad_queries
    config = {"home_city": "Madrid", "search_language": "es", "home_country": "Spain"}
    result = generate_broad_queries(config, "2026-04-04", "2026-04-05")
    filled = [t.format(**result["vars"]) for t in result["templates"]]
    combined = " ".join(filled)
    assert "eventos" in combined
    assert "abril" in result["vars"]["date"]
    assert "imprezy" not in combined


def test_generate_broad_queries_unknown_lang_falls_back_to_english():
    from weekend_scout.cities import generate_broad_queries
    config = {"home_city": "Somewhere", "search_language": "xx", "home_country": "Xland"}
    result = generate_broad_queries(config, "2026-03-28", "2026-03-29")
    filled = [t.format(**result["vars"]) for t in result["templates"]]
    combined = " ".join(filled)
    assert "outdoor events" in combined
    assert "outdoor events weekend March 28, 2026 Xland" in combined
    assert "imprezy" not in combined


def test_generate_broad_queries_japanese():
    from weekend_scout.cities import generate_broad_queries
    config = {"home_city": "Tokyo", "search_language": "ja", "home_country": "Japan"}
    result = generate_broad_queries(config, "2026-04-11", "2026-04-12")
    filled = [t.format(**result["vars"]) for t in result["templates"]]
    combined = " ".join(filled)
    assert "週末" in combined
    assert result["vars"]["date"] == "2026年4月11日"
    assert result["vars"]["month"] == "4月"
    assert "March" not in result["vars"]["date"]


def test_generate_broad_queries_localizes_english_home_city_name(tmp_path, monkeypatch):
    import weekend_scout.cities as cities_module
    from weekend_scout.cities import generate_broad_queries

    p = tmp_path / "cities.txt"
    p.write_text(_make_geonames_row("1", "Київ", "Kyiv", "50.45", "30.52", "UA", "2967000"), encoding="utf-8")
    monkeypatch.setattr(cities_module, "ensure_geonames", lambda: p)

    config = {"home_city": "Kyiv", "search_language": "uk", "home_country": "Ukraine"}
    result = generate_broad_queries(config, "2026-04-11", "2026-04-12")
    filled = [t.format(**result["vars"]) for t in result["templates"]]
    combined = " ".join(filled)

    assert result["vars"]["city"] == "Київ"
    assert "Київ" in combined


def test_generate_targeted_template_returns_string():
    from weekend_scout.cities import generate_targeted_template
    result = generate_targeted_template("pl")
    assert isinstance(result, str)
    assert "{city}" in result
    assert "{date}" in result
    assert "imprezy" in result  # Polish keyword


def test_generate_targeted_template_german():
    from weekend_scout.cities import generate_targeted_template
    result = generate_targeted_template("de")
    assert "Veranstaltungen" in result or "Freiluft" in result
    assert "imprezy" not in result
    assert "{city}" in result


def test_generate_targeted_template_italian():
    from weekend_scout.cities import generate_targeted_template
    result = generate_targeted_template("it")
    assert "eventi" in result
    assert "{city}" in result
    assert "{date}" in result


def test_generate_targeted_template_spanish():
    from weekend_scout.cities import generate_targeted_template
    result = generate_targeted_template("es")
    assert "eventos" in result
    assert "{city}" in result
    assert "{date}" in result


def test_generate_targeted_template_english_fallback():
    from weekend_scout.cities import generate_targeted_template
    result = generate_targeted_template("xx")
    assert "outdoor events" in result
    assert "imprezy" not in result
    assert "{city}" in result


def test_generate_targeted_template_japanese():
    from weekend_scout.cities import generate_targeted_template
    result = generate_targeted_template("ja")
    assert result == "{city} イベント {date}"


def test_generate_targeted_template_korean():
    from weekend_scout.cities import generate_targeted_template
    result = generate_targeted_template("ko")
    assert result == "{city} 행사 {date}"


def test_generate_targeted_template_fills_correctly():
    from weekend_scout.cities import generate_targeted_template
    tmpl = generate_targeted_template("pl")
    query = tmpl.format(city="Łódź", date="28 marca 2026")
    assert "Łódź" in query
    assert "28 marca 2026" in query


def test_generate_targeted_by_country_builds_localized_entries():
    from weekend_scout.cities import generate_targeted_by_country

    config = {
        "home_city": "Berlin",
        "home_country": "Germany",
        "search_language": "de",
    }
    cities = {"tier1": ["Potsdam|DE"], "tier2": [], "tier3": ["Szczecin|PL"]}

    result = generate_targeted_by_country(config, cities, "2026-03-28")

    assert result["DE"]["template"] == "{city} Veranstaltungen Freiluft {date}"
    assert "März" in result["DE"]["date"]
    assert result["PL"]["template"] == "{city} imprezy plenerowe {date}"
    assert "marca" in result["PL"]["date"]


def test_generate_targeted_by_country_falls_back_to_english_for_unknown_country():
    from weekend_scout.cities import generate_targeted_by_country

    config = {
        "home_city": "Berlin",
        "home_country": "Germany",
        "search_language": "de",
    }
    cities = {"tier1": ["Somewhere|XX"], "tier2": [], "tier3": []}

    result = generate_targeted_by_country(config, cities, "2026-03-28")

    assert result["XX"]["template"] == "{city} outdoor events {date}"
    assert "March" in result["XX"]["date"]


def test_generate_targeted_by_country_supports_new_countries():
    from weekend_scout.cities import generate_targeted_by_country

    config = {
        "home_city": "Tokyo",
        "home_country": "Japan",
        "search_language": "ja",
    }
    cities = {
        "tier1": ["Toronto|CA", "Seoul|KR"],
        "tier2": ["New York|US"],
        "tier3": ["London|GB"],
    }

    result = generate_targeted_by_country(config, cities, "2026-04-11")

    assert result["JP"]["template"] == "{city} イベント {date}"
    assert result["JP"]["date"] == "2026年4月11日"
    assert result["KR"]["template"] == "{city} 행사 {date}"
    assert result["KR"]["date"] == "2026년 4월 11일"
    assert result["US"]["template"] == "{city} outdoor events {date}"
    assert "April" in result["US"]["date"]
    assert result["CA"]["language"] == "en"
    assert result["GB"]["language"] == "en"


def test_build_targeted_city_cards_localizes_english_city_name_for_query(tmp_path, monkeypatch):
    import weekend_scout.__main__ as main_mod
    import weekend_scout.cities as cities_module

    p = tmp_path / "cities.txt"
    p.write_text(_make_geonames_row("1", "Київ", "Kyiv", "50.45", "30.52", "UA", "2967000"), encoding="utf-8")
    monkeypatch.setattr(cities_module, "ensure_geonames", lambda: p)

    cards = main_mod._build_targeted_city_cards(
        ["Kyiv|UA"],
        searches_this_week=[],
        targeted_by_country={
            "UA": {
                "template": "{city} заходи просто неба {date}",
                "date": "11 квітня 2026",
                "language": "uk",
            }
        },
        geonames_path=p,
    )

    assert len(cards) == 1
    assert cards[0]["city_name"] == "Kyiv"
    assert "Київ" in cards[0]["query"]


def test_find_city_candidates_includes_new_supported_countries(tmp_path):
    from weekend_scout.cities import find_city_candidates

    content = "\n".join([
        _make_geonames_row("1", "Toronto", "Toronto", "43.65", "-79.38", "CA", "2731571"),
        _make_geonames_row("2", "Tokyo", "Tokyo", "35.69", "139.69", "JP", "13929286"),
        _make_geonames_row("3", "Seoul", "Seoul", "37.57", "126.98", "KR", "9776000"),
    ])
    p = tmp_path / "cities.txt"
    p.write_text(content, encoding="utf-8")

    toronto = find_city_candidates("Toronto", p)
    tokyo = find_city_candidates("Tokyo", p)
    seoul = find_city_candidates("Seoul", p)

    assert toronto[0]["country_name"] == "Canada"
    assert toronto[0]["language"] == "en"
    assert tokyo[0]["country_name"] == "Japan"
    assert tokyo[0]["language"] == "ja"
    assert seoul[0]["country_name"] == "South Korea"
    assert seoul[0]["language"] == "ko"


def test_find_city_coords_returns_highest_population(tmp_path):
    from weekend_scout.cities import find_city_coords
    content = "\n".join([
        _make_geonames_row("1", "Berlin", "Berlin", "52.52", "13.40", "DE", "3500000"),
        _make_geonames_row("2", "Berlin", "Berlin", "39.30", "-74.93", "US", "10000"),
    ])
    p = tmp_path / "cities.txt"
    p.write_text(content, encoding="utf-8")
    result = find_city_coords("Berlin", p)
    assert result is not None
    assert result["population"] == 3500000
    assert result["country"] == "DE"


@pytest.mark.parametrize(
    ("city_name", "country_filter", "lang", "expected"),
    [
        ("Kyiv", "Ukraine", "uk", "Київ"),
        ("Moscow", "Russia", "ru", "Москва"),
        ("Athens", "Greece", "el", "Αθήνα"),
        ("Tokyo", "Japan", "ja", "東京"),
        ("Seoul", "South Korea", "ko", "서울"),
        ("Kyiv", "Ukraine", "en", "Kyiv"),
        ("Moscow", "Russia", "en", "Moscow"),
        ("Athens", "Greece", "en", "Athens"),
        ("Tokyo", "Japan", "en", "Tokyo"),
        ("Seoul", "South Korea", "en", "Seoul"),
    ],
)
def test_get_query_city_name_prefers_native_or_ascii_by_language(tmp_path, city_name, country_filter, lang, expected):
    from weekend_scout.cities import get_query_city_name

    content = "\n".join(
        [
            _make_geonames_row("1", "Київ", "Kyiv", "50.45", "30.52", "UA", "2967000"),
            _make_geonames_row("2", "Москва", "Moscow", "55.75", "37.62", "RU", "11920000"),
            _make_geonames_row("3", "Αθήνα", "Athens", "37.98", "23.72", "GR", "3153000"),
            _make_geonames_row("4", "東京", "Tokyo", "35.69", "139.69", "JP", "13929286"),
            _make_geonames_row("5", "서울", "Seoul", "37.57", "126.98", "KR", "9776000"),
        ]
    )
    p = tmp_path / "cities.txt"
    p.write_text(content, encoding="utf-8")

    result = get_query_city_name(city_name, lang=lang, geonames_path=p, country_filter=country_filter)

    assert result == expected


def test_get_query_city_name_falls_back_to_original_input_on_miss(tmp_path):
    from weekend_scout.cities import get_query_city_name

    p = tmp_path / "cities.txt"
    p.write_text(_make_geonames_row("1", "Warszawa", "Warsaw", "52.23", "21.01", "PL", "1700000"), encoding="utf-8")

    assert get_query_city_name("Unknown City", lang="pl", geonames_path=p) == "Unknown City"


def test_get_query_city_name_uses_language_tagged_alternate_name_for_belarus(tmp_path, monkeypatch):
    import weekend_scout.cities as cities_module
    from weekend_scout.cities import get_query_city_name

    p = tmp_path / "cities.txt"
    p.write_text(
        _make_geonames_row("1", "Lida", "Lida", "53.8833", "25.2997", "BY", "101616"),
        encoding="utf-8",
    )
    alt_path = tmp_path / "BY.txt"
    alt_path.write_text(
        "\n".join(
            [
                _make_alternate_name_row("1", "1", "ru", "\u041b\u0438\u0434\u0430", is_preferred=True),
                _make_alternate_name_row("2", "1", "be", "\u041b\u0456\u0434\u0430", is_preferred=True),
            ]
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(cities_module, "ensure_country_alternate_names", lambda _code, force=False: alt_path)

    result = get_query_city_name("Lida", lang="be", geonames_path=p, country_filter="Belarus")

    assert result == "\u041b\u0456\u0434\u0430"


def test_get_query_city_name_falls_back_when_alternate_name_download_fails(tmp_path, monkeypatch):
    import weekend_scout.cities as cities_module
    from weekend_scout.cities import get_query_city_name

    p = tmp_path / "cities.txt"
    p.write_text(
        _make_geonames_row("1", "Lida", "Lida", "53.8833", "25.2997", "BY", "101616"),
        encoding="utf-8",
    )
    monkeypatch.setattr(
        cities_module,
        "ensure_country_alternate_names",
        lambda _code, force=False: (_ for _ in ()).throw(RuntimeError("download failed")),
    )

    result = get_query_city_name("Lida", lang="be", geonames_path=p, country_filter="Belarus")

    assert result == "Lida"


def test_download_country_alternate_names_extracts_exact_country_member(tmp_path, monkeypatch):
    import weekend_scout.cities as cities_module

    fake_zip = _write_fake_country_alternate_zip(
        tmp_path,
        "BY",
        {
            "readme.txt": "Readme for GeoNames Gazetteer extract files\n",
            "BY.txt": _make_alternate_name_row("1", "1", "be", "\u041b\u0456\u0434\u0430", is_preferred=True) + "\n",
        },
    )
    monkeypatch.setattr(cities_module, "_alternate_names_dir", lambda: tmp_path)
    monkeypatch.setattr(cities_module, "_download_zip", lambda _url, zip_path: shutil.copyfile(fake_zip, zip_path))

    extracted = cities_module.download_country_alternate_names("BY", force=True)

    assert extracted.read_text(encoding="utf-8").startswith("1\t1\tbe\t")


def test_download_country_alternate_names_fails_when_country_member_missing(tmp_path, monkeypatch):
    import weekend_scout.cities as cities_module

    fake_zip = _write_fake_country_alternate_zip(
        tmp_path,
        "BY",
        {"readme.txt": "Readme for GeoNames Gazetteer extract files\n"},
    )
    monkeypatch.setattr(cities_module, "_alternate_names_dir", lambda: tmp_path)
    monkeypatch.setattr(cities_module, "_download_zip", lambda _url, zip_path: shutil.copyfile(fake_zip, zip_path))

    with pytest.raises(RuntimeError, match=r"missing BY\.txt"):
        cities_module.download_country_alternate_names("BY", force=True)


def test_ensure_country_alternate_names_replaces_invalid_cached_file(tmp_path, monkeypatch):
    import weekend_scout.cities as cities_module

    cached = tmp_path / "BY.txt"
    cached.write_text("Readme for GeoNames Gazetteer extract files\n", encoding="utf-8")
    fake_zip = _write_fake_country_alternate_zip(
        tmp_path,
        "BY",
        {
            "readme.txt": "Readme for GeoNames Gazetteer extract files\n",
            "BY.txt": _make_alternate_name_row("1", "1", "be", "\u041b\u0456\u0434\u0430", is_preferred=True) + "\n",
        },
    )
    monkeypatch.setattr(cities_module, "_alternate_names_dir", lambda: tmp_path)
    monkeypatch.setattr(cities_module, "_download_zip", lambda _url, zip_path: shutil.copyfile(fake_zip, zip_path))

    ensured = cities_module.ensure_country_alternate_names("BY")

    assert ensured == cached
    assert "Readme for GeoNames" not in cached.read_text(encoding="utf-8")
    parsed = cities_module.parse_country_alternate_names(cached)
    assert parsed[1][0]["name"] == "\u041b\u0456\u0434\u0430"


def test_get_query_city_name_downloads_and_extracts_country_alternate_names_end_to_end(tmp_path, monkeypatch):
    import weekend_scout.cities as cities_module
    from weekend_scout.cities import get_query_city_name

    p = tmp_path / "cities.txt"
    p.write_text(
        _make_geonames_row("1", "Lida", "Lida", "53.8833", "25.2997", "BY", "101616"),
        encoding="utf-8",
    )
    fake_zip = _write_fake_country_alternate_zip(
        tmp_path,
        "BY",
        {
            "readme.txt": "Readme for GeoNames Gazetteer extract files\n",
            "BY.txt": _make_alternate_name_row("1", "1", "be", "\u041b\u0456\u0434\u0430", is_preferred=True) + "\n",
        },
    )
    alternates_dir = tmp_path / "alternatenames"
    alternates_dir.mkdir()
    monkeypatch.setattr(cities_module, "_alternate_names_dir", lambda: alternates_dir)
    monkeypatch.setattr(cities_module, "_download_zip", lambda _url, zip_path: shutil.copyfile(fake_zip, zip_path))

    result = get_query_city_name("Lida", lang="be", geonames_path=p, country_filter="Belarus")

    assert result == "\u041b\u0456\u0434\u0430"
    assert (alternates_dir / "BY.txt").read_text(encoding="utf-8").startswith("1\t1\tbe\t")


def test_find_city_coords_matches_exact_alternate_name(tmp_path):
    from weekend_scout.cities import find_city_coords

    p = tmp_path / "cities.txt"
    p.write_text(
        _make_geonames_row(
            "1",
            "Baranovichi",
            "Baranovichi",
            "53.1327",
            "26.0139",
            "BY",
            "168772",
            alternate_names="\u0411\u0430\u0440\u0430\u043d\u043e\u0432\u0438\u0447\u0438,\u0411\u0430\u0440\u0430\u043d\u0430\u0432\u0456\u0447\u044b",
        ),
        encoding="utf-8",
    )

    assert find_city_coords("\u0411\u0430\u0440\u0430\u043d\u043e\u0432\u0438\u0447\u0438", p, country_filter="Belarus") is not None
    assert find_city_coords("\u0411\u0430\u0440\u0430\u043d\u0430\u0432\u0456\u0447\u044b", p, country_filter="Belarus") is not None


def test_find_city_candidates_matches_exact_alternate_name(tmp_path):
    from weekend_scout.cities import find_city_candidates

    p = tmp_path / "cities.txt"
    p.write_text(
        _make_geonames_row(
            "1",
            "Novogrudok",
            "Novogrudok",
            "53.5942",
            "25.8191",
            "BY",
            "28591",
            alternate_names="\u041d\u043e\u0432\u043e\u0433\u0440\u0443\u0434\u043e\u043a,\u041d\u0430\u0432\u0430\u0433\u0440\u0443\u0434\u0430\u043a",
        ),
        encoding="utf-8",
    )

    matches = find_city_candidates("\u041d\u0430\u0432\u0430\u0433\u0440\u0443\u0434\u0430\u043a", p, country_filter="Belarus")

    assert matches
    assert matches[0]["country_name"] == "Belarus"


def test_find_city_coords_country_filter_prefers_requested_country(tmp_path):
    from weekend_scout.cities import find_city_coords

    content = "\n".join([
        _make_geonames_row("1", "London", "London", "51.51", "-0.13", "GB", "8982000"),
        _make_geonames_row("2", "London", "London", "42.98", "-81.25", "CA", "422324"),
    ])
    p = tmp_path / "cities.txt"
    p.write_text(content, encoding="utf-8")

    result = find_city_coords("London", p, country_filter="Canada")

    assert result is not None
    assert result["country"] == "CA"


def test_find_city_coords_returns_none_for_unknown_city(tmp_path):
    from weekend_scout.cities import find_city_coords
    p = tmp_path / "cities.txt"
    p.write_text(_make_geonames_row(), encoding="utf-8")
    assert find_city_coords("Atlantis", p) is None


def test_find_city_coords_matches_native_name(tmp_path):
    from weekend_scout.cities import find_city_coords
    content = _make_geonames_row("1", "Łódź", "Lodz", "51.76", "19.46", "PL", "672185")
    p = tmp_path / "cities.txt"
    p.write_text(content, encoding="utf-8")
    assert find_city_coords("Łódź", p) is not None
    assert find_city_coords("Lodz", p) is not None


def test_get_city_list_uses_cache(tmp_path, monkeypatch):
    import weekend_scout.config as cfg_module
    from weekend_scout.cities import get_city_list

    monkeypatch.setattr(cfg_module, "get_cache_dir", lambda _config: tmp_path)

    # Write a pre-built cache file
    cache_data = {
        "generated": "2026-03-26T10:00:00",
        "home_city": "Warsaw",
        "radius_km": 150,
        "country": "Poland",
        "cities": [
            {"name": "Lodz", "name_local": "Łódź", "country": "PL",
             "lat": 51.76, "lon": 19.46, "population": 672185,
             "distance_km": 131, "tier": 1},
            {"name": "Plock", "name_local": "Płock", "country": "PL",
             "lat": 52.55, "lon": 19.71, "population": 119709,
             "distance_km": 108, "tier": 2},
        ],
    }
    cache_file = tmp_path / "cities_Warsaw_150.json"
    cache_file.write_text(json.dumps(cache_data), encoding="utf-8")

    config = {
        "home_city": "Warsaw",
        "radius_km": 150,
        "home_coordinates": {"lat": 52.23, "lon": 21.01},
        "home_country": "Poland",
    }
    result = get_city_list(config)

    assert "tier1" in result
    assert "tier2" in result
    assert "Łódź" in result["tier1"]
    assert "Płock" in result["tier2"]


def test_get_city_list_uses_cache(tmp_path, monkeypatch):
    import weekend_scout.config as cfg_module
    from weekend_scout.cities import get_city_list

    monkeypatch.setattr(cfg_module, "get_cache_dir", lambda _config: tmp_path)

    cache_data = {
        "generated": "2026-03-26T10:00:00",
        "home_city": "Warsaw",
        "radius_km": 150,
        "country": "Poland",
        "cities": [
            {"name": "Lodz", "name_local": "Lodz", "country": "PL",
             "lat": 51.76, "lon": 19.46, "population": 672185,
             "distance_km": 131, "tier": 1},
            {"name": "Plock", "name_local": "Plock", "country": "PL",
             "lat": 52.55, "lon": 19.71, "population": 119709,
             "distance_km": 108, "tier": 2},
        ],
    }
    cache_file = tmp_path / "cities_Warsaw_150.json"
    cache_file.write_text(json.dumps(cache_data), encoding="utf-8")

    config = {
        "home_city": "Warsaw",
        "radius_km": 150,
        "home_coordinates": {"lat": 52.23, "lon": 21.01},
        "home_country": "Poland",
    }
    result = get_city_list(config)

    assert result["tier1"] == ["Lodz|PL"]
    assert result["tier2"] == ["Plock|PL"]


# --- download_geonames retry ---

def test_download_geonames_retries_on_network_error(tmp_path, monkeypatch):
    import requests as req_module
    import time
    from weekend_scout import cities as cities_module
    monkeypatch.setattr(cities_module, "_geonames_dir", lambda: tmp_path)
    monkeypatch.setattr(cities_module, "_RETRY_DELAYS", (0, 0))
    monkeypatch.setattr(time, "sleep", lambda _: None)

    call_count = 0

    def fake_get(*a, **kw):
        nonlocal call_count
        call_count += 1
        raise req_module.ConnectionError("network down")

    monkeypatch.setattr(req_module, "get", fake_get)

    with pytest.raises(RuntimeError, match="GeoNames download failed"):
        cities_module.download_geonames(force=True)

    assert call_count == 3
    assert not (tmp_path / "cities15000.zip").exists()


def test_download_geonames_succeeds_on_second_attempt(tmp_path, monkeypatch):
    import io
    import requests as req_module
    import time
    import zipfile as zf_module
    from weekend_scout import cities as cities_module
    monkeypatch.setattr(cities_module, "_geonames_dir", lambda: tmp_path)
    monkeypatch.setattr(cities_module, "_RETRY_DELAYS", (0, 0))
    monkeypatch.setattr(time, "sleep", lambda _: None)

    attempt = [0]

    def fake_get(*a, **kw):
        attempt[0] += 1
        if attempt[0] == 1:
            raise req_module.ConnectionError("transient")
        buf = io.BytesIO()
        with zf_module.ZipFile(buf, "w") as z:
            z.writestr("cities15000.txt", "fake content")
        buf.seek(0)

        class FakeResp:
            def raise_for_status(self): pass
            def iter_content(self, chunk_size=None):
                yield buf.read()
        return FakeResp()

    monkeypatch.setattr(req_module, "get", fake_get)
    result = cities_module.download_geonames(force=True)
    assert result.exists()
    assert attempt[0] == 2
