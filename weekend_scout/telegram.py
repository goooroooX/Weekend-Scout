"""Telegram message formatting and sending for Weekend Scout.

Uses the Telegram Bot API directly via the requests library.
No async, no python-telegram-bot dependency.

Message length limit: 4096 characters per Telegram message.
If the message is longer, it is split at section boundaries.
"""

from __future__ import annotations

import datetime
import sys
from typing import Any

import requests

TELEGRAM_MAX_LENGTH = 4096
TELEGRAM_API_BASE = "https://api.telegram.org"

# Hardcoded English month names — avoids locale-dependent strftime on Windows.
_MONTHS = [
    "January", "February", "March", "April", "May", "June",
    "July", "August", "September", "October", "November", "December",
]
_DAYS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]

_MARKDOWN_SPECIAL = str.maketrans({"_": r"\_", "*": r"\*", "`": r"\`", "[": r"\["})


def _escape_markdown(text: str) -> str:
    """Escape characters that break Telegram's Markdown parser."""
    return text.translate(_MARKDOWN_SPECIAL)


def _day_abbr(iso_date: str) -> str:
    """Return short weekday abbreviation for an ISO date string."""
    d = datetime.date.fromisoformat(iso_date)
    return _DAYS[d.weekday()]


def split_message(message: str, max_length: int = TELEGRAM_MAX_LENGTH) -> list[str]:
    """Split a long message into parts at section boundaries.

    Splits prefer double-newline paragraph breaks, falling back to
    single newlines if necessary.

    Args:
        message: Full message text.
        max_length: Maximum character length per part.

    Returns:
        List of message part strings, each <= max_length characters.
    """
    if not message:
        return [""]
    if len(message) <= max_length:
        return [message]

    window = message[:max_length]

    # Prefer splitting at a paragraph break
    split_at = window.rfind("\n\n")
    if split_at == -1:
        # Fall back to any line break
        split_at = window.rfind("\n")
    if split_at == -1:
        # Hard split as last resort
        split_at = max_length

    head = message[:split_at].rstrip()
    tail = message[split_at:].lstrip()

    parts = [head] if head else []
    if tail:
        parts.extend(split_message(tail, max_length))
    return parts if parts else [""]


def send_telegram(config: dict[str, Any], message: str) -> bool:
    """Send a message to the configured Telegram chat.

    Automatically splits messages longer than 4096 characters.

    Args:
        config: Loaded configuration dictionary (must contain
                telegram_bot_token and telegram_chat_id).
        message: Formatted message text (Markdown).

    Returns:
        True if all parts were sent successfully, False otherwise.
    """
    token = config.get("telegram_bot_token", "")
    chat_id = config.get("telegram_chat_id", "")

    if not token or not chat_id:
        print("send_telegram: telegram_bot_token or telegram_chat_id not configured", file=sys.stderr)
        return False

    url = f"{TELEGRAM_API_BASE}/bot{token}/sendMessage"
    parts = split_message(message)

    try:
        for part in parts:
            resp = requests.post(
                url,
                json={
                    "chat_id": chat_id,
                    "text": part,
                    "parse_mode": "Markdown",
                    "disable_web_page_preview": True,
                },
                timeout=30,
            )
            if resp.status_code != 200:
                return False
    except requests.RequestException:
        return False

    return True


def format_event_block(event: dict[str, Any]) -> str:
    """Format a single event as a Telegram message block.

    Args:
        event: Event dict from the cache (or with the same keys).

    Returns:
        Formatted string block for the event (no leading number/letter).
    """
    lines: list[str] = []

    name = _escape_markdown(event.get("event_name") or "")
    lines.append(name)

    # Venue | Day(s) Time
    venue = event.get("location_name") or ""
    time_info = event.get("time_info") or ""
    start_date = event.get("start_date") or ""
    end_date = event.get("end_date") or ""

    day_str = ""
    if start_date:
        day_str = _day_abbr(start_date)
        if end_date and end_date != start_date:
            day_str = f"{day_str}-{_day_abbr(end_date)}"

    venue_time_parts = []
    if venue:
        venue_time_parts.append(_escape_markdown(venue))
    day_time = " ".join(filter(None, [day_str, time_info]))
    if day_time:
        venue_time_parts.append(day_time)
    if venue_time_parts:
        lines.append("   " + " | ".join(venue_time_parts))

    # Description (truncated)
    desc = event.get("description") or ""
    if desc:
        if len(desc) > 120:
            desc = desc[:117] + "..."
        lines.append("   " + _escape_markdown(desc))

    # Cost
    free_entry = event.get("free_entry")
    if free_entry is True or free_entry == 1:
        lines.append("   Free entry")
    elif free_entry is False or free_entry == 0:
        lines.append("   Paid")

    # URL (not escaped — URLs should remain as-is)
    url = event.get("source_url") or ""
    if url:
        lines.append("   " + url)

    return "\n".join(lines)


def format_scout_message(
    home_city: str,
    saturday: str,
    sunday: str,
    city_events: list[dict[str, Any]],
    trip_options: list[dict[str, Any]],
) -> str:
    """Format the full Weekend Scout message.

    Args:
        home_city: Name of the home city.
        saturday: ISO date string of target Saturday.
        sunday: ISO date string of target Sunday.
        city_events: Up to 3 top-ranked home city events.
        trip_options: Up to 3 road trip option dicts.
            Each trip dict should have keys:
              name (str), route (str), events (str), timing (str).

    Returns:
        Fully formatted message string.
    """
    sat = datetime.date.fromisoformat(saturday)
    sun = datetime.date.fromisoformat(sunday)
    month = _MONTHS[sat.month - 1]
    if sat.month == sun.month:
        date_range = f"{month} {sat.day}-{sun.day}, {sat.year}"
    else:
        sun_month = _MONTHS[sun.month - 1]
        date_range = f"{month} {sat.day} - {sun_month} {sun.day}, {sat.year}"

    header = f"Weekend Scout | {date_range}"

    if not city_events and not trip_options:
        return (
            f"{header}\n\n"
            "No events found for this weekend.\n\n"
            "---\nScouted by Weekend Scout"
        )

    sections: list[str] = [header]

    if city_events:
        sections.append(f"\nIN {home_city.upper()}:\n")
        for i, event in enumerate(city_events[:3], 1):
            block = format_event_block(event)
            # Indent all lines after the first (which gets the number prefix)
            block_lines = block.split("\n")
            numbered = f"{i}. {block_lines[0]}"
            if len(block_lines) > 1:
                numbered += "\n" + "\n".join(block_lines[1:])
            sections.append(numbered)

    if trip_options:
        sections.append("\nROAD TRIPS:\n")
        letters = "ABCDEFGHIJ"
        for i, trip in enumerate(trip_options[:3]):
            letter = letters[i]
            name = _escape_markdown(trip.get("name") or "")
            route = _escape_markdown(trip.get("route") or "")
            events_text = _escape_markdown(trip.get("events") or "")
            timing = _escape_markdown(trip.get("timing") or "")
            parts = [f"{letter}. {name}"]
            if route:
                parts.append(f"   {route}")
            if events_text:
                parts.append(f"   {events_text}")
            if timing:
                parts.append(f"   {timing}")
            sections.append("\n".join(parts))

    sections.append("\n---\nScouted by Weekend Scout")
    return "\n\n".join(sections)
