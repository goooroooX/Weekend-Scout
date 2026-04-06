"""Centralized CLI failure handling and Python diagnostics logging."""

from __future__ import annotations

import datetime
import json
import traceback
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, NoReturn


_REDACT_KEYS = ("token", "password", "secret", "authorization")


@dataclass
class CommandFailure(Exception):
    """Structured operational failure for CLI commands."""

    message: str
    error_code: str = "command_failed"
    detail: dict[str, Any] = field(default_factory=dict)
    retryable: bool = False
    run_id: str | None = None
    phase: str | None = None
    target_weekend: str | None = None
    config: dict[str, Any] | None = None

    def __post_init__(self) -> None:
        super().__init__(self.message)


def _fallback_cache_dir() -> Path:
    from weekend_scout.config import get_config_dir

    cache_dir = get_config_dir() / "cache"
    cache_dir.mkdir(parents=True, exist_ok=True)
    return cache_dir


def get_failure_log_path(config: dict[str, Any] | None = None) -> Path:
    """Return the path to python_failures.jsonl."""
    if config is not None:
        try:
            from weekend_scout.config import get_cache_dir

            cache_dir = get_cache_dir(config)
            cache_dir.mkdir(parents=True, exist_ok=True)
            return cache_dir / "python_failures.jsonl"
        except Exception:
            pass
    return _fallback_cache_dir() / "python_failures.jsonl"


def _redact_string(value: str) -> str:
    redacted = value
    token_like = []
    for part in value.split():
        if ":" in part and part.count(":") == 1:
            left, right = part.split(":", 1)
            if left.isdigit() and len(right) >= 20:
                token_like.append(part)
    for token in token_like:
        redacted = redacted.replace(token, "<redacted-token>")
    if len(redacted) > 300:
        return redacted[:297] + "..."
    return redacted


def _sanitize_value(value: Any, *, key: str | None = None, depth: int = 0) -> Any:
    if depth > 4:
        return "<truncated>"
    if isinstance(value, dict):
        sanitized = {}
        for child_key, child_value in value.items():
            child_key_str = str(child_key)
            if any(marker in child_key_str.lower() for marker in _REDACT_KEYS):
                sanitized[child_key_str] = "<redacted>"
            else:
                sanitized[child_key_str] = _sanitize_value(child_value, key=child_key_str, depth=depth + 1)
        return sanitized
    if isinstance(value, list):
        if len(value) > 10:
            return {
                "type": "list",
                "length": len(value),
                "preview": [_sanitize_value(item, depth=depth + 1) for item in value[:3]],
            }
        return [_sanitize_value(item, depth=depth + 1) for item in value]
    if isinstance(value, tuple):
        return [_sanitize_value(item, depth=depth + 1) for item in value]
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, str):
        if key and any(marker in key.lower() for marker in _REDACT_KEYS):
            return "<redacted>"
        return _redact_string(value)
    if isinstance(value, (int, float, bool)) or value is None:
        return value
    return _redact_string(str(value))


def _failure_id() -> str:
    return f"wsf_{uuid.uuid4().hex[:12]}"


def log_python_failure(
    *,
    command: str,
    error_code: str,
    message: str,
    safe_context: dict[str, Any] | None = None,
    exception: BaseException | None = None,
    config: dict[str, Any] | None = None,
    run_id: str | None = None,
    phase: str | None = None,
    target_weekend: str | None = None,
    retryable: bool = False,
) -> str:
    """Persist one Python failure with mirrored run-scoped action-log context."""
    failure_id = _failure_id()
    safe_context = _sanitize_value(safe_context or {})
    exception_type = type(exception).__name__ if exception else None
    tb_text = None
    if exception is not None:
        tb_text = _redact_string("".join(traceback.format_exception(type(exception), exception, exception.__traceback__)))

    entry = {
        "ts": datetime.datetime.now().isoformat(timespec="seconds"),
        "failure_id": failure_id,
        "command": command,
        "run_id": run_id,
        "phase": phase,
        "target_weekend": target_weekend,
        "error_code": error_code,
        "message": _redact_string(message),
        "safe_context": safe_context,
        "exception_type": exception_type,
        "traceback": tb_text,
        "retryable": retryable,
    }

    path = get_failure_log_path(config)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(entry, ensure_ascii=False) + "\n")

    if run_id:
        try:
            from weekend_scout.cache import log_action

            mirror_config = config if config is not None else {"_cache_dir": path.parent}
            log_action(
                mirror_config,
                "command_failed",
                phase=phase,
                detail={
                    "command": command,
                    "error_code": error_code,
                    "message": _redact_string(message),
                    "failure_id": failure_id,
                },
                run_id=run_id,
                source="python",
                target_weekend=target_weekend,
            )
        except Exception:
            pass

    return failure_id


def emit_command_failure(
    *,
    command: str,
    error_code: str,
    message: str,
    detail: dict[str, Any] | None = None,
    retryable: bool = False,
    exception: BaseException | None = None,
    config: dict[str, Any] | None = None,
    run_id: str | None = None,
    phase: str | None = None,
    target_weekend: str | None = None,
) -> NoReturn:
    """Log and print one structured CLI failure, then exit non-zero."""
    safe_context = detail or {}
    failure_id = log_python_failure(
        command=command,
        error_code=error_code,
        message=message,
        safe_context=safe_context,
        exception=exception,
        config=config,
        run_id=run_id,
        phase=phase,
        target_weekend=target_weekend,
        retryable=retryable,
    )
    print(
        json.dumps(
            {
                "error": message,
                "error_code": error_code,
                "failure_id": failure_id,
                "detail": {
                    "retryable": retryable,
                    "context": _sanitize_value(detail or {}),
                },
            },
            ensure_ascii=False,
        )
    )
    raise SystemExit(1)

