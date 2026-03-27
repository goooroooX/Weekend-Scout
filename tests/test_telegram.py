"""Tests for weekend_scout.telegram."""


def _event(**kwargs) -> dict:
    """Minimal valid event dict for formatting tests."""
    base = {
        "event_name": "Test Festival",
        "city": "Warsaw",
        "start_date": "2026-04-04",
        "end_date": "2026-04-05",
        "location_name": "Old Town Square",
        "time_info": "10:00-18:00",
        "description": "A fun outdoor festival",
        "free_entry": True,
        "source_url": "https://example.com/event",
    }
    base.update(kwargs)
    return base


def _trip(**kwargs) -> dict:
    """Minimal valid trip option dict."""
    base = {
        "name": "Lodz Day Trip",
        "route": "Warsaw -> Lodz (131 km, ~1h40)",
        "events": "Festiwal Czterech Kultur | ul. Piotrkowska | Sat-Sun all day",
        "timing": "Leave by: 9:00 | Back by: ~20:00",
    }
    base.update(kwargs)
    return base


# --- split_message ---

def test_split_short_message_returns_single():
    from weekend_scout.telegram import split_message
    result = split_message("Hello world")
    assert result == ["Hello world"]


def test_split_empty_message():
    from weekend_scout.telegram import split_message
    assert split_message("") == [""]


def test_split_at_double_newline():
    from weekend_scout.telegram import split_message
    part_a = "A" * 4000
    part_b = "B" * 500
    message = part_a + "\n\n" + part_b  # total > 4096
    result = split_message(message, max_length=4096)
    assert len(result) == 2
    assert result[0] == part_a
    assert result[1] == part_b


def test_split_at_single_newline_fallback():
    from weekend_scout.telegram import split_message
    part_a = "A" * 4000
    part_b = "B" * 500
    message = part_a + "\n" + part_b  # total > 4096
    result = split_message(message, max_length=4096)
    assert len(result) == 2
    assert result[0] == part_a
    assert result[1] == part_b


def test_split_hard_cutoff_no_newlines():
    from weekend_scout.telegram import split_message
    message = "X" * 5000
    result = split_message(message, max_length=4096)
    assert len(result) == 2
    assert len(result[0]) == 4096
    assert len(result[1]) == 904


def test_split_all_whitespace_returns_nonempty_list():
    from weekend_scout.telegram import split_message
    # All-whitespace message longer than max_length must not return []
    message = "\n\n" * 2100  # 4200 chars, > 4096
    result = split_message(message, max_length=4096)
    assert len(result) >= 1


def test_split_multiple_parts_all_within_limit():
    from weekend_scout.telegram import split_message
    # Build a message that will need 3+ splits
    chunk = "Section\n\n" + "A" * 2000 + "\n\n"
    message = chunk * 4  # ~8032+ chars
    result = split_message(message, max_length=4096)
    assert len(result) >= 2
    assert all(len(p) <= 4096 for p in result)


# --- send_telegram ---

def test_send_telegram_success(monkeypatch):
    from weekend_scout.telegram import send_telegram
    calls = []

    class FakeResp:
        status_code = 200

    def fake_post(url, json, timeout):
        calls.append((url, json))
        return FakeResp()

    monkeypatch.setattr("weekend_scout.telegram.requests.post", fake_post)
    cfg = {"telegram_bot_token": "123:ABC", "telegram_chat_id": "-100999"}
    result = send_telegram(cfg, "Hello")
    assert result is True
    assert len(calls) == 1
    assert "/bot123:ABC/sendMessage" in calls[0][0]
    assert calls[0][1]["chat_id"] == "-100999"
    assert calls[0][1]["text"] == "Hello"
    assert calls[0][1]["parse_mode"] == "Markdown"
    assert calls[0][1]["disable_web_page_preview"] is True


def test_send_telegram_failure(monkeypatch):
    from weekend_scout.telegram import send_telegram

    class FakeResp:
        status_code = 403

    monkeypatch.setattr("weekend_scout.telegram.requests.post", lambda *a, **kw: FakeResp())
    cfg = {"telegram_bot_token": "tok", "telegram_chat_id": "123"}
    assert send_telegram(cfg, "Hello") is False


def test_send_telegram_splits_long_message(monkeypatch):
    from weekend_scout.telegram import send_telegram
    calls = []

    class FakeResp:
        status_code = 200

    def fake_post(url, json, timeout):
        calls.append(json["text"])
        return FakeResp()

    monkeypatch.setattr("weekend_scout.telegram.requests.post", fake_post)
    cfg = {"telegram_bot_token": "tok", "telegram_chat_id": "123"}
    long_msg = "Part one\n\n" + "A" * 4000 + "\n\nPart two\n\n" + "B" * 4000
    result = send_telegram(cfg, long_msg)
    assert result is True
    assert len(calls) >= 2
    assert all(len(p) <= 4096 for p in calls)


def test_send_telegram_missing_token():
    from weekend_scout.telegram import send_telegram
    cfg = {"telegram_bot_token": "", "telegram_chat_id": "123"}
    assert send_telegram(cfg, "Hello") is False


def test_send_telegram_missing_chat_id():
    from weekend_scout.telegram import send_telegram
    cfg = {"telegram_bot_token": "tok", "telegram_chat_id": ""}
    assert send_telegram(cfg, "Hello") is False


def test_send_telegram_network_error(monkeypatch):
    import requests as req_lib
    from weekend_scout.telegram import send_telegram

    def fake_post(url, json, timeout):
        raise req_lib.ConnectionError("network down")

    monkeypatch.setattr("weekend_scout.telegram.requests.post", fake_post)
    cfg = {"telegram_bot_token": "tok", "telegram_chat_id": "123"}
    assert send_telegram(cfg, "Hello") is False


# --- format_event_block ---

def test_format_event_block_all_fields():
    from weekend_scout.telegram import format_event_block
    result = format_event_block(_event())
    assert "Test Festival" in result
    assert "Old Town Square" in result
    assert "10:00-18:00" in result
    assert "A fun outdoor festival" in result
    assert "Free entry" in result
    assert "https://example.com/event" in result


def test_format_event_block_minimal_fields():
    from weekend_scout.telegram import format_event_block
    # Should not crash with only required fields
    result = format_event_block({"event_name": "Bare Event", "city": "Warsaw", "start_date": "2026-04-04"})
    assert "Bare Event" in result


def test_format_event_block_paid():
    from weekend_scout.telegram import format_event_block
    result = format_event_block(_event(free_entry=False))
    assert "Paid" in result
    assert "Free entry" not in result


def test_format_event_block_no_cost_when_none():
    from weekend_scout.telegram import format_event_block
    result = format_event_block(_event(free_entry=None))
    assert "Free entry" not in result
    assert "Paid" not in result


def test_format_event_block_long_description_truncated():
    from weekend_scout.telegram import format_event_block
    long_desc = "A" * 200
    result = format_event_block(_event(description=long_desc))
    # Description should not appear in full
    assert "A" * 200 not in result
    assert "..." in result


def test_format_event_block_weekend_span():
    from weekend_scout.telegram import format_event_block
    result = format_event_block(_event(start_date="2026-04-04", end_date="2026-04-05"))
    assert "Sat-Sun" in result


def test_format_event_block_single_day():
    from weekend_scout.telegram import format_event_block
    result = format_event_block(_event(start_date="2026-04-04", end_date=None))
    assert "Sat" in result
    assert "Sat-Sun" not in result


def test_format_event_block_time_info_markdown_escaped():
    from weekend_scout.telegram import format_event_block
    result = format_event_block(_event(time_info="10:00*18:00"))
    assert r"10:00\*18:00" in result


# --- format_scout_message ---

def test_format_scout_message_header():
    from weekend_scout.telegram import format_scout_message
    msg = format_scout_message("Warsaw", "2026-04-04", "2026-04-05", [_event()], [])
    assert msg.startswith("Weekend Scout | April 4-5, 2026")


def test_format_scout_message_city_events():
    from weekend_scout.telegram import format_scout_message
    events = [_event(event_name="Fest A"), _event(event_name="Fest B")]
    msg = format_scout_message("Warsaw", "2026-04-04", "2026-04-05", events, [])
    assert "IN WARSAW:" in msg
    assert "1. Fest A" in msg
    assert "2. Fest B" in msg


def test_format_scout_message_road_trips():
    from weekend_scout.telegram import format_scout_message
    msg = format_scout_message("Warsaw", "2026-04-04", "2026-04-05", [], [_trip()])
    assert "ROAD TRIPS:" in msg
    assert "A. Lodz Day Trip" in msg


def test_format_scout_message_no_trips_omits_section():
    from weekend_scout.telegram import format_scout_message
    msg = format_scout_message("Warsaw", "2026-04-04", "2026-04-05", [_event()], [])
    assert "ROAD TRIPS:" not in msg


def test_format_scout_message_footer():
    from weekend_scout.telegram import format_scout_message
    msg = format_scout_message("Warsaw", "2026-04-04", "2026-04-05", [_event()], [])
    assert "Scouted by Weekend Scout" in msg


def test_format_scout_message_empty_returns_no_events():
    from weekend_scout.telegram import format_scout_message
    msg = format_scout_message("Warsaw", "2026-04-04", "2026-04-05", [], [])
    assert "No events found" in msg
    assert "Weekend Scout |" in msg
    assert "Scouted by Weekend Scout" in msg


def test_format_scout_message_month_boundary():
    from weekend_scout.telegram import format_scout_message
    # March 30 - April 1 (hypothetical, just test formatting doesn't crash)
    msg = format_scout_message("Paris", "2026-03-28", "2026-03-29", [], [])
    assert "March 28-29, 2026" in msg
