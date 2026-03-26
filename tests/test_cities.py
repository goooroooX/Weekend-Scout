"""Tests for weekend_scout.cities."""

import json
import pytest
from pathlib import Path


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


def test_get_region_name_custom_path(tmp_path):
    from weekend_scout.cities import get_region_name
    regions = {"cities": {"TestCity": "TestRegion"}}
    p = tmp_path / "regions.json"
    p.write_text(json.dumps(regions), encoding="utf-8")
    assert get_region_name("TestCity", regions_path=p) == "TestRegion"
    assert get_region_name("Unknown", regions_path=p) == "Unknown"


def test_format_date_local_polish():
    from weekend_scout.cities import format_date_local
    assert format_date_local("2026-03-28", "pl") == "28 marca 2026"
    assert format_date_local("2026-12-01", "pl") == "1 grudnia 2026"


def test_format_date_local_english():
    from weekend_scout.cities import format_date_local
    assert format_date_local("2026-03-28", "en") == "March 28, 2026"
    assert format_date_local("2026-01-05", "en") == "January 5, 2026"


def test_format_date_local_german():
    from weekend_scout.cities import format_date_local
    assert format_date_local("2026-03-28", "de") == "28. März 2026"


def test_format_date_local_unknown_lang_falls_back_to_english():
    from weekend_scout.cities import format_date_local
    result = format_date_local("2026-03-28", "xx")
    assert "March" in result
    assert "2026" in result


def _make_geonames_row(
    geonameid="1234", name="Łódź", asciiname="Lodz",
    lat="51.7592", lon="19.4560", country="PL", population="672185",
    feature_code="PPLA", admin2="", admin3="",
) -> str:
    cols = [
        geonameid, name, asciiname, "",   # 0-3
        lat, lon,                          # 4-5
        "P", feature_code,                 # 6-7
        country, "",                       # 8-9
        "", admin2, admin3, "",            # 10-13
        population, "", "100",             # 14-16
        "Europe/Warsaw", "2024-01-01",     # 17-18
    ]
    return "\t".join(cols)


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
    monkeypatch.setattr(cities_module, "_DATA_DIR", tmp_path)

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
    assert "Wola" not in all_names       # district filtered
    assert "Pruszkow" in all_names       # real city kept


def test_generate_broad_queries_returns_list():
    from weekend_scout.cities import generate_broad_queries
    config = {
        "home_city": "Warsaw",
        "search_language": "pl",
        "home_country": "Poland",
    }
    result = generate_broad_queries(config, "2026-03-28", "2026-03-29")
    assert isinstance(result, list)
    assert len(result) == 4
    assert any("Mazowsze" in q for q in result)
    assert any("outdoor" in q.lower() for q in result)


def test_generate_broad_queries_contains_date():
    from weekend_scout.cities import generate_broad_queries
    config = {"home_city": "Warsaw", "search_language": "pl", "home_country": "Poland"}
    result = generate_broad_queries(config, "2026-03-28", "2026-03-29")
    combined = " ".join(result)
    assert "marca" in combined   # Polish month
    assert "March" in combined   # English fallback query


def test_generate_broad_queries_german():
    from weekend_scout.cities import generate_broad_queries
    config = {"home_city": "Berlin", "search_language": "de", "home_country": "Germany"}
    result = generate_broad_queries(config, "2026-03-28", "2026-03-29")
    combined = " ".join(result)
    assert len(result) == 4
    assert "Veranstaltungen" in combined or "Freiluft" in combined
    assert "imprezy" not in combined   # no Polish
    assert "März" in combined          # German month in local queries
    assert "March" in combined         # English fallback still present


def test_generate_broad_queries_french():
    from weekend_scout.cities import generate_broad_queries
    config = {"home_city": "Paris", "search_language": "fr", "home_country": "France"}
    result = generate_broad_queries(config, "2026-03-28", "2026-03-29")
    combined = " ".join(result)
    assert "événements" in combined or "plein air" in combined
    assert "imprezy" not in combined
    assert "March" in combined  # English fallback


def test_generate_broad_queries_unknown_lang_falls_back_to_english():
    from weekend_scout.cities import generate_broad_queries
    config = {"home_city": "Somewhere", "search_language": "xx", "home_country": "Xland"}
    result = generate_broad_queries(config, "2026-03-28", "2026-03-29")
    combined = " ".join(result)
    assert "outdoor events" in combined
    assert "imprezy" not in combined


def test_generate_targeted_queries_returns_dict():
    from weekend_scout.cities import generate_targeted_queries
    result = generate_targeted_queries(["Łódź", "Radom"], "pl", "2026-03-28")
    assert isinstance(result, dict)
    assert set(result.keys()) == {"Łódź", "Radom"}
    assert isinstance(result["Łódź"], list)
    assert len(result["Łódź"]) == 1
    assert "Łódź" in result["Łódź"][0]
    assert "imprezy" in result["Łódź"][0]  # Polish keyword


def test_generate_targeted_queries_german():
    from weekend_scout.cities import generate_targeted_queries
    result = generate_targeted_queries(["München", "Hamburg"], "de", "2026-03-28")
    combined = " ".join(result["München"] + result["Hamburg"])
    assert "Veranstaltungen" in combined or "Freiluft" in combined
    assert "imprezy" not in combined


def test_generate_targeted_queries_english_fallback():
    from weekend_scout.cities import generate_targeted_queries
    result = generate_targeted_queries(["Dublin"], "xx", "2026-03-28")
    assert "outdoor events" in result["Dublin"][0]
    assert "imprezy" not in result["Dublin"][0]


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
