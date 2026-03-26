"""Tests for weekend_scout.distance."""

import datetime
from unittest.mock import patch

import pytest


def test_haversine_km_same_point():
    from weekend_scout.distance import haversine_km
    assert haversine_km(52.23, 21.01, 52.23, 21.01) == pytest.approx(0.0, abs=0.001)


def test_haversine_km_warsaw_lodz():
    from weekend_scout.distance import haversine_km
    dist = haversine_km(52.2297, 21.0122, 51.7592, 19.4560)
    assert 115 < dist < 135


def test_haversine_km_known_distance():
    from weekend_scout.distance import haversine_km
    dist = haversine_km(52.2297, 21.0122, 50.0647, 19.9450)
    assert 240 < dist < 270


def test_estimated_drive_minutes_short():
    from weekend_scout.distance import estimated_drive_minutes
    assert estimated_drive_minutes(20) == pytest.approx(30.0)


def test_estimated_drive_minutes_medium():
    from weekend_scout.distance import estimated_drive_minutes
    assert estimated_drive_minutes(60) == pytest.approx(60.0)


def test_estimated_drive_minutes_long():
    from weekend_scout.distance import estimated_drive_minutes
    assert estimated_drive_minutes(120) == pytest.approx(90.0)


def test_format_drive_time_minutes_only():
    from weekend_scout.distance import format_drive_time
    assert format_drive_time(45) == "45min"
    assert format_drive_time(15) == "15min"
    assert format_drive_time(59) == "59min"


def test_format_drive_time_hours():
    from weekend_scout.distance import format_drive_time
    assert format_drive_time(60) == "1h00"
    assert format_drive_time(100) == "1h40"
    assert format_drive_time(135) == "2h15"


def test_next_weekend_dates_returns_saturday_sunday():
    from weekend_scout.distance import next_weekend_dates

    # Mock today to a known Wednesday (2026-03-25)
    with patch("weekend_scout.distance.datetime") as mock_dt:
        mock_dt.date.today.return_value = datetime.date(2026, 3, 25)
        mock_dt.timedelta = datetime.timedelta
        sat, sun = next_weekend_dates()

    assert sat == "2026-03-28"
    assert sun == "2026-03-29"


def test_next_weekend_dates_skips_current_saturday():
    from weekend_scout.distance import next_weekend_dates

    # Mock today to Saturday — should return NEXT Saturday, not today
    with patch("weekend_scout.distance.datetime") as mock_dt:
        mock_dt.date.today.return_value = datetime.date(2026, 3, 28)  # Saturday
        mock_dt.timedelta = datetime.timedelta
        sat, sun = next_weekend_dates()

    assert sat == "2026-04-04"
    assert sun == "2026-04-05"
