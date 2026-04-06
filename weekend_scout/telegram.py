"""Telegram message formatting and sending for Weekend Scout.

Uses the Telegram Bot API directly via the requests library.
No async, no python-telegram-bot dependency.

Message length limit: 4096 characters per Telegram message.
If the message is longer, it is split at section boundaries.

Formatting: HTML parse_mode (not Markdown/MarkdownV2).
Only <, >, & need escaping via html.escape().
Supports: <b>bold</b>, <i>italic</i>, <a href="url">text</a>
"""

from __future__ import annotations

import datetime
import html
import re
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
_TRIP_PREFIX_RE = re.compile(r"^(?:[A-Z]|\d+)\.\s+")


def _day_abbr(iso_date: str) -> str:
    """Return short weekday abbreviation for an ISO date string."""
    d = datetime.date.fromisoformat(iso_date)
    return _DAYS[d.weekday()]


def _normalize_trip_name(name: str) -> str:
    """Strip any pre-numbered trip prefix so the formatter owns labeling."""
    return _TRIP_PREFIX_RE.sub("", name).strip()


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


def _safe_error_text(value: object) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    if len(text) > 200:
        return text[:197] + "..."
    return text


def _telegram_response_description(resp: object) -> str | None:
    json_reader = getattr(resp, "json", None)
    if callable(json_reader):
        try:
            payload = json_reader()
        except ValueError:
            payload = None
        if isinstance(payload, dict):
            description = _safe_error_text(payload.get("description"))
            if description:
                return description
    text = _safe_error_text(getattr(resp, "text", None))
    return text


def _network_error_code(exc: requests.RequestException) -> str:
    message = str(exc).lower()
    if isinstance(exc, requests.Timeout):
        return "telegram_timeout"
    if "10013" in message or "access permissions" in message:
        return "telegram_network_blocked"
    return "telegram_network_error"


def send_telegram(config: dict[str, Any], message: str) -> dict[str, Any]:
    """Send a message to the configured Telegram chat.

    Automatically splits messages longer than 4096 characters.

    Args:
        config: Loaded configuration dictionary (must contain
                telegram_bot_token and telegram_chat_id).
        message: Formatted message text (HTML).

    Returns:
        Structured send result with authoritative reason and safe diagnostics.
    """
    token = config.get("telegram_bot_token", "")
    chat_id = config.get("telegram_chat_id", "")

    if not token or not chat_id:
        missing = []
        if not token:
            missing.append("telegram_bot_token")
        if not chat_id:
            missing.append("telegram_chat_id")
        return {
            "sent": False,
            "reason": "telegram_not_configured",
            "error_code": "telegram_not_configured",
            "status_code": None,
            "error": f"Missing config: {', '.join(missing)}",
            "parts_sent": 0,
        }

    url = f"{TELEGRAM_API_BASE}/bot{token}/sendMessage"
    parts = split_message(message)
    parts_sent = 0

    try:
        for part in parts:
            resp = requests.post(
                url,
                json={
                    "chat_id": chat_id,
                    "text": part,
                    "parse_mode": "HTML",
                    "disable_web_page_preview": True,
                },
                timeout=30,
            )
            if resp.status_code != 200:
                return {
                    "sent": False,
                    "reason": "send_failed",
                    "error_code": "telegram_http_error",
                    "status_code": resp.status_code,
                    "error": _telegram_response_description(resp) or f"HTTP {resp.status_code}",
                    "parts_sent": parts_sent,
                }
            json_reader = getattr(resp, "json", None)
            if callable(json_reader):
                try:
                    payload = json_reader()
                except ValueError:
                    return {
                        "sent": False,
                        "reason": "send_failed",
                        "error_code": "telegram_bad_response",
                        "status_code": resp.status_code,
                        "error": "Telegram returned a non-JSON success response",
                        "parts_sent": parts_sent,
                    }
                if isinstance(payload, dict) and payload.get("ok") is False:
                    return {
                        "sent": False,
                        "reason": "send_failed",
                        "error_code": "telegram_bad_response",
                        "status_code": resp.status_code,
                        "error": _safe_error_text(payload.get("description")) or "Telegram returned ok=false",
                        "parts_sent": parts_sent,
                    }
            parts_sent += 1
    except requests.RequestException as exc:
        return {
            "sent": False,
            "reason": "send_failed",
            "error_code": _network_error_code(exc),
            "status_code": None,
            "error": _safe_error_text(exc) or type(exc).__name__,
            "parts_sent": parts_sent,
        }

    return {
        "sent": True,
        "reason": "sent",
        "error_code": None,
        "status_code": None,
        "error": None,
        "parts_sent": len(parts),
    }


def format_event_block(event: dict[str, Any]) -> str:
    """Format a single event as a Telegram HTML message block.

    Args:
        event: Event dict from the cache (or with the same keys).

    Returns:
        Formatted HTML string block for the event (no leading number/letter).
    """
    lines: list[str] = []

    name = html.escape(event.get("event_name") or "")
    lines.append(f"<b>{name}</b>")

    # Venue | Day(s) Time
    venue = html.escape(event.get("location_name") or "")
    time_info = html.escape(event.get("time_info") or "")
    start_date = event.get("start_date") or ""
    end_date = event.get("end_date") or ""

    day_str = ""
    if start_date:
        day_str = _day_abbr(start_date)
        if end_date and end_date != start_date:
            day_str = f"{day_str}-{_day_abbr(end_date)}"

    venue_time_parts = []
    if venue:
        venue_time_parts.append(venue)
    day_time = " ".join(filter(None, [day_str, time_info]))
    if day_time:
        venue_time_parts.append(day_time)

    # Inline link tag appended to description or venue line
    url = event.get("source_url") or ""
    link_tag = f' [<a href="{html.escape(url)}">link</a>]' if url else ""

    if venue_time_parts:
        venue_line = "   " + " | ".join(venue_time_parts)
        if not (event.get("description") or ""):
            # No description: attach link to venue line
            venue_line += link_tag
            link_tag = ""
        lines.append(venue_line)

    # Description (truncated) + inline link
    desc = event.get("description") or ""
    if desc:
        if len(desc) > 120:
            desc = desc[:117] + "..."
        lines.append("   " + html.escape(desc) + link_tag)

    # Cost
    free_entry = event.get("free_entry")
    if free_entry is True or free_entry == 1:
        lines.append("   Free")
    elif free_entry is False or free_entry == 0:
        lines.append("   Paid")

    return "\n".join(lines)


def format_scout_message(
    home_city: str,
    saturday: str,
    sunday: str,
    city_events: list[dict[str, Any]],
    trip_options: list[dict[str, Any]],
    low_results_hint: bool = False,
    hint_max_searches: int = 50,
    hint_max_fetches: int = 50,
) -> str:
    """Format the full Weekend Scout message as HTML.

    Args:
        home_city: Name of the home city.
        saturday: ISO date string of target Saturday.
        sunday: ISO date string of target Sunday.
        city_events: Top-ranked home city events (caller controls count).
        trip_options: Road trip option dicts (caller controls count).
            Each trip dict should have keys:
              name (str), route (str), events (str), timing (str).
            Optional: url (str) appended as [link] on the events line.
        low_results_hint: When True, appends a hint suggesting the user
            increase the search budget.

    Returns:
        Fully formatted HTML message string.
    """
    sat = datetime.date.fromisoformat(saturday)
    sun = datetime.date.fromisoformat(sunday)
    month = _MONTHS[sat.month - 1]
    if sat.month == sun.month:
        date_range = f"{month} {sat.day}-{sun.day}, {sat.year}"
    else:
        sun_month = _MONTHS[sun.month - 1]
        date_range = f"{month} {sat.day} - {sun_month} {sun.day}, {sat.year}"

    header = f"<b>Weekend Scout | {date_range}</b>"

    if not city_events and not trip_options:
        hint = (
            "\n\n<i>No events found. To discover more, increase your search budget:\n"
            f"python -m weekend_scout config max_searches {hint_max_searches}\n"
            f"python -m weekend_scout config max_fetches {hint_max_fetches}</i>"
            if low_results_hint else ""
        )
        return (
            f"{header}\n\n"
            f"No events found for this weekend.{hint}\n\n"
            "<i>Scouted by Weekend Scout</i>"
        )

    sections: list[str] = [header]

    if city_events:
        sections.append(f"<b>IN {html.escape(home_city.upper())}:</b>")
        for i, event in enumerate(city_events, 1):
            block = format_event_block(event)
            # Prepend number to the first line (which has the <b>name</b>)
            block_lines = block.split("\n")
            block_lines[0] = f"{i}. {block_lines[0]}"
            sections.append("\n".join(block_lines))

    if trip_options:
        sections.append("<b>ROAD TRIPS:</b>")
        for i, trip in enumerate(trip_options, 1):
            name = html.escape(_normalize_trip_name(trip.get("name") or ""))
            route = html.escape(trip.get("route") or "")
            events_text = html.escape(trip.get("events") or "")
            timing = html.escape(trip.get("timing") or "")
            trip_url = trip.get("url") or ""
            parts = [f"{i:02d}. <b>{name}</b>"]
            if route:
                parts.append(f"   {route}")
            if events_text:
                trip_link = f' [<a href="{html.escape(trip_url)}">link</a>]' if trip_url else ""
                parts.append(f"   {events_text}{trip_link}")
            if timing:
                parts.append(f"   {timing}")
            sections.append("\n".join(parts))

    if low_results_hint:
        total = len(city_events) + len(trip_options)
        sections.append(
            f"<i>Only {total} event(s) found. To discover more, increase your search budget:\n"
            f"python -m weekend_scout config max_searches {hint_max_searches}\n"
            f"python -m weekend_scout config max_fetches {hint_max_fetches}</i>"
        )

    sections.append("<i>Scouted by Weekend Scout</i>")
    return "\n\n".join(sections)


def format_scout_preview(
    home_city: str,
    saturday: str,
    sunday: str,
    city_events: list[dict[str, Any]],
    trip_options: list[dict[str, Any]],
    low_results_hint: bool = False,
    hint_max_searches: int = 50,
    hint_max_fetches: int = 50,
) -> str:
    """Format a plain-text preview of the scout digest for CLI/chat display."""
    sat = datetime.date.fromisoformat(saturday)
    sun = datetime.date.fromisoformat(sunday)
    month = _MONTHS[sat.month - 1]
    if sat.month == sun.month:
        date_range = f"{month} {sat.day}-{sun.day}, {sat.year}"
    else:
        sun_month = _MONTHS[sun.month - 1]
        date_range = f"{month} {sat.day} - {sun_month} {sun.day}, {sat.year}"

    lines: list[str] = [f"Weekend Scout | {date_range}"]

    if not city_events and not trip_options:
        lines.extend(["", "No events found for this weekend."])
        if low_results_hint:
            lines.extend([
                "",
                "Only 0 event(s) found. To discover more, increase your search budget:",
                f"python -m weekend_scout config max_searches {hint_max_searches}",
                f"python -m weekend_scout config max_fetches {hint_max_fetches}",
            ])
        lines.extend(["", "Scouted by Weekend Scout"])
        return "\n".join(lines)

    if city_events:
        lines.extend(["", f"IN {home_city.upper()}"])
        for i, event in enumerate(city_events, 1):
            lines.append("")
            lines.append(f"{i}. {event.get('event_name', '')}")
            venue_parts = []
            venue = event.get("location_name") or ""
            if venue:
                venue_parts.append(venue)
            start_date = event.get("start_date") or ""
            end_date = event.get("end_date") or ""
            day_str = ""
            if start_date:
                day_str = _day_abbr(start_date)
                if end_date and end_date != start_date:
                    day_str = f"{day_str}-{_day_abbr(end_date)}"
            time_info = event.get("time_info") or ""
            if day_str and time_info:
                venue_parts.append(f"{day_str} {time_info}")
            elif day_str:
                venue_parts.append(day_str)
            elif time_info:
                venue_parts.append(time_info)
            if venue_parts:
                lines.append(f"   {' | '.join(venue_parts)}")
            desc = event.get("description") or ""
            if desc:
                if len(desc) > 120:
                    desc = desc[:117] + "..."
                lines.append(f"   {desc}")
            source_url = event.get("source_url") or ""
            if source_url:
                lines.append(f"   {source_url}")

    if trip_options:
        lines.extend(["", "ROAD TRIPS"])
        for i, trip in enumerate(trip_options, 1):
            lines.append("")
            lines.append(f"{i:02d}. {_normalize_trip_name(trip.get('name') or '')}")
            route = trip.get("route") or ""
            if route:
                lines.append(f"   {route}")
            events_text = trip.get("events") or ""
            if events_text:
                lines.append(f"   {events_text}")
            timing = trip.get("timing") or ""
            if timing:
                lines.append(f"   {timing}")
            trip_url = trip.get("url") or ""
            if trip_url:
                lines.append(f"   {trip_url}")

    if low_results_hint:
        total = len(city_events) + len(trip_options)
        lines.extend([
            "",
            f"Only {total} event(s) found. To discover more, increase your search budget:",
            f"python -m weekend_scout config max_searches {hint_max_searches}",
            f"python -m weekend_scout config max_fetches {hint_max_fetches}",
        ])

    lines.extend(["", "Scouted by Weekend Scout"])
    return "\n".join(lines)
