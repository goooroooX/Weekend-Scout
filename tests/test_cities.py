"""Tests for weekend_scout.cities."""

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
    pass


def test_get_region_name_unknown_city_returns_city():
    pass


def test_format_date_local_polish():
    pass


def test_format_date_local_english():
    pass


def test_parse_geonames_file(tmp_path):
    pass


def test_generate_broad_queries_returns_list():
    pass


def test_generate_targeted_queries_returns_dict():
    pass


def test_get_city_list_uses_cache(tmp_path):
    pass
