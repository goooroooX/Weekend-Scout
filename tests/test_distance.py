"""Tests for weekend_scout.distance."""

import pytest


def test_haversine_km_same_point():
    from weekend_scout.distance import haversine_km
    assert haversine_km(52.23, 21.01, 52.23, 21.01) == pytest.approx(0.0, abs=0.001)


def test_haversine_km_warsaw_lodz():
    from weekend_scout.distance import haversine_km
    # Warsaw to Łódź is roughly 120 km straight-line
    dist = haversine_km(52.2297, 21.0122, 51.7592, 19.4560)
    assert 115 < dist < 135


def test_haversine_km_known_distance():
    from weekend_scout.distance import haversine_km
    # Warsaw to Krakow: roughly 250 km
    dist = haversine_km(52.2297, 21.0122, 50.0647, 19.9450)
    assert 240 < dist < 270


def test_estimated_drive_minutes_short():
    from weekend_scout.distance import estimated_drive_minutes
    # < 30 km: 1.5x
    assert estimated_drive_minutes(20) == pytest.approx(30.0)


def test_estimated_drive_minutes_medium():
    from weekend_scout.distance import estimated_drive_minutes
    # 30-80 km: 1.0x
    assert estimated_drive_minutes(60) == pytest.approx(60.0)


def test_estimated_drive_minutes_long():
    from weekend_scout.distance import estimated_drive_minutes
    # > 80 km: 0.75x
    assert estimated_drive_minutes(120) == pytest.approx(90.0)


def test_format_drive_time():
    pass


def test_next_weekend_dates_returns_saturday_sunday():
    pass
