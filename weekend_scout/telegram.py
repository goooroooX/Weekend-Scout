"""Telegram message formatting and sending for Weekend Scout.

Uses the Telegram Bot API directly via the requests library.
No async, no python-telegram-bot dependency.

Message length limit: 4096 characters per Telegram message.
If the message is longer, it is split at section boundaries.
"""

from __future__ import annotations

from typing import Any

import requests

TELEGRAM_MAX_LENGTH = 4096
TELEGRAM_API_BASE = "https://api.telegram.org"


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
    pass


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
    pass


def format_event_block(event: dict[str, Any]) -> str:
    """Format a single event as a Telegram message block.

    Args:
        event: Event dict from the cache.

    Returns:
        Formatted string block for the event.
    """
    pass


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

    Returns:
        Fully formatted message string.
    """
    pass
