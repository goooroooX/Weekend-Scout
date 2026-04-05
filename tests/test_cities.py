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
