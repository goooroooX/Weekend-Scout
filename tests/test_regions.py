"""Tests for weekend_scout.regions."""


def test_get_region_known_cities():
    from weekend_scout.regions import get_region

    assert get_region("Warsaw") == "Mazowsze"
    assert get_region("Berlin") == "Brandenburg"
    assert get_region("Paris").endswith("le-de-France")
    assert get_region("Rome") == "Lazio"
    assert get_region("Madrid") == "Community of Madrid"


def test_get_region_new_supported_cities():
    from weekend_scout.regions import get_region

    assert get_region("New York") == "Northeast"
    assert get_region("Toronto") == "Ontario"
    assert get_region("Tokyo") == "Kanto"
    assert get_region("Seoul") == "Seoul Capital Area"


def test_get_region_native_names():
    from weekend_scout.regions import get_region

    assert get_region("Warszawa") == "Mazowsze"
    assert get_region("Roma") == "Lazio"
    assert get_region("Lisboa") == "Greater Lisbon"
    assert get_region("東京") == "Kanto"
    assert get_region("서울") == "Seoul Capital Area"


def test_get_region_fallback_to_city_name():
    from weekend_scout.regions import get_region

    assert get_region("Atlantis") == "Atlantis"
    assert get_region("UnknownCity") == "UnknownCity"


def test_get_region_custom_fallback():
    from weekend_scout.regions import get_region

    assert get_region("Atlantis", fallback="Unknown Region") == "Unknown Region"


def test_get_region_case_sensitive():
    from weekend_scout.regions import get_region

    assert get_region("warsaw") == "warsaw"
    assert get_region("Warsaw") == "Mazowsze"


def test_regions_dict_has_all_36_supported_countries():
    from weekend_scout.regions import REGIONS

    representative = [
        "Warsaw",      # Poland
        "New York",    # United States
        "Toronto",     # Canada
        "London",      # United Kingdom
        "Dublin",      # Ireland
        "Sydney",      # Australia
        "Auckland",    # New Zealand
        "Singapore",   # Singapore
        "Tokyo",       # Japan
        "Seoul",       # South Korea
        "Berlin",      # Germany
        "Paris",       # France
        "Prague",      # Czech Republic
        "Bratislava",  # Slovakia
        "Vienna",      # Austria
        "Budapest",    # Hungary
        "Kyiv",        # Ukraine
        "Vilnius",     # Lithuania
        "Riga",        # Latvia
        "Tallinn",     # Estonia
        "Minsk",       # Belarus
        "Rome",        # Italy
        "Madrid",      # Spain
        "Lisbon",      # Portugal
        "Amsterdam",   # Netherlands
        "Stockholm",   # Sweden
        "Oslo",        # Norway
        "Copenhagen",  # Denmark
        "Helsinki",    # Finland
        "Bucharest",   # Romania
        "Zagreb",      # Croatia
        "Sofia",       # Bulgaria
        "Belgrade",    # Serbia
        "Athens",      # Greece
        "Istanbul",    # Turkey
        "Moscow",      # Russia
    ]
    for city in representative:
        assert city in REGIONS, f"{city} not found in REGIONS"
