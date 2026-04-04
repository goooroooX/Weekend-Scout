"""Run-scoped candidate persistence for Weekend Scout discovery sessions."""

from __future__ import annotations

import datetime
import json
import re
from pathlib import Path
from typing import Any


SESSION_FILE_SUFFIX = ".candidates.json"
SESSION_RETENTION_DAYS = 14
CONFIDENCE_RANK = {
    "unverified": 0,
    "possible": 0,
    "likely": 1,
    "confirmed": 2,
}
STRONG_OVERRIDE_FIELDS: tuple[str, ...] = (
    "start_date",
    "end_date",
    "time_info",
    "location_name",
    "lat",
    "lon",
    "source_url",
    "source_name",
)


def _cache_dir(config: dict[str, Any]) -> Path:
    """Return the active cache directory, respecting test overrides."""
    if "_cache_dir" in config:
        return Path(config["_cache_dir"])
    from weekend_scout.config import get_cache_dir

    return get_cache_dir(config)


def get_runs_dir(config: dict[str, Any]) -> Path:
    """Return the directory that stores run-scoped candidate session files."""
    return _cache_dir(config) / "runs"


def get_session_path(config: dict[str, Any], run_id: str) -> Path:
    """Return the path to one run's candidate session file."""
    return get_runs_dir(config) / f"{run_id}{SESSION_FILE_SUFFIX}"


def cleanup_stale_sessions(
    config: dict[str, Any], *, days: int = SESSION_RETENTION_DAYS
) -> list[str]:
    """Delete stale candidate session files and return removed filenames."""
    runs_dir = get_runs_dir(config)
    try:
        items = list(runs_dir.iterdir())
    except OSError:
        return []

    cutoff = datetime.datetime.now() - datetime.timedelta(days=days)
    removed: list[str] = []
    for path in items:
        if not path.is_file() or not path.name.endswith(SESSION_FILE_SUFFIX):
            continue
        try:
            modified = datetime.datetime.fromtimestamp(path.stat().st_mtime)
        except OSError:
            continue
        if modified >= cutoff:
            continue
        try:
            path.unlink(missing_ok=True)
            removed.append(path.name)
        except OSError:
            continue
    return removed


def _default_state(run_id: str, target_weekend: str) -> dict[str, Any]:
    return {
        "run_id": run_id,
        "target_weekend": target_weekend,
        "updated_at": datetime.datetime.now().isoformat(timespec="seconds"),
        "candidates": [],
    }


def _write_state(path: Path, state: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    state["updated_at"] = datetime.datetime.now().isoformat(timespec="seconds")
    path.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")


def load_session_state(
    config: dict[str, Any],
    run_id: str,
    *,
    target_weekend: str | None = None,
    create: bool = False,
) -> dict[str, Any] | None:
    """Load one run's session state, optionally creating an empty file."""
    path = get_session_path(config, run_id)
    if not path.exists():
        if not create:
            return None
        if target_weekend is None:
            raise ValueError("target_weekend is required when creating a session file")
        state = _default_state(run_id, target_weekend)
        _write_state(path, state)
        return state

    state = json.loads(path.read_text(encoding="utf-8"))
    if "candidates" not in state or not isinstance(state["candidates"], list):
        state["candidates"] = []
    if not state.get("run_id"):
        state["run_id"] = run_id
    if target_weekend and not state.get("target_weekend"):
        state["target_weekend"] = target_weekend
        _write_state(path, state)
    return state


def export_session_candidates(config: dict[str, Any], run_id: str) -> list[dict[str, Any]]:
    """Return all canonical candidates currently stored for one run."""
    state = load_session_state(config, run_id)
    if state is None:
        return []
    return _sorted_candidates(state.get("candidates", []))


def query_session_candidates(config: dict[str, Any], run_id: str) -> list[dict[str, Any]]:
    """Return candidates for one run that overlap the run's target weekend."""
    state = load_session_state(config, run_id)
    if state is None:
        return []
    saturday = state.get("target_weekend")
    if not isinstance(saturday, str) or not saturday:
        return []
    return _sorted_candidates(
        [candidate for candidate in state.get("candidates", []) if _overlaps_weekend(candidate, saturday)]
    )


def get_session_covered_cities(config: dict[str, Any], run_id: str) -> list[str]:
    """Return covered city names from one run's session candidates for the target weekend."""
    return sorted({str(candidate.get("city")) for candidate in query_session_candidates(config, run_id) if candidate.get("city")})


def get_session_candidate_count(config: dict[str, Any], run_id: str) -> int:
    """Return the total canonical candidate count for one run."""
    return len(export_session_candidates(config, run_id))


def upsert_session_candidates(
    config: dict[str, Any],
    run_id: str,
    target_weekend: str,
    candidates: list[dict[str, Any]],
) -> dict[str, int]:
    """Upsert candidates into the run-scoped session file."""
    state = load_session_state(config, run_id, target_weekend=target_weekend, create=True)
    if state is None:
        raise RuntimeError("Failed to create session state")

    stored_candidates = list(state.get("candidates", []))
    added = 0
    updated = 0

    for incoming in candidates:
        _validate_candidate(incoming)
        match_idx = _find_match_index(stored_candidates, incoming, target_weekend)
        if match_idx is None:
            stored_candidates.append(dict(incoming))
            added += 1
            continue

        merged = _merge_candidate(stored_candidates[match_idx], incoming)
        if merged != stored_candidates[match_idx]:
            stored_candidates[match_idx] = merged
            updated += 1

    state["candidates"] = _sorted_candidates(stored_candidates)
    _write_state(get_session_path(config, run_id), state)
    return {
        "added": added,
        "updated": updated,
        "events_discovered": added,
        "candidate_count": len(state["candidates"]),
    }


def _validate_candidate(candidate: dict[str, Any]) -> None:
    for key in ("event_name", "city", "start_date"):
        value = candidate.get(key)
        if not isinstance(value, str) or not value.strip():
            raise ValueError(f"candidate missing required field {key!r}")


def _normalize_text(value: str) -> str:
    return re.sub(r"[^\w_]", "", re.sub(r"\s+", "_", value.strip().lower()))


def _confidence_rank(value: Any) -> int:
    if not isinstance(value, str):
        return 0
    return CONFIDENCE_RANK.get(value.strip().lower(), 0)


def _has_value(value: Any) -> bool:
    if value is None:
        return False
    if isinstance(value, str):
        return value.strip() != ""
    return True


def _sorted_candidates(candidates: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return sorted(
        (dict(candidate) for candidate in candidates),
        key=lambda candidate: (
            str(candidate.get("start_date", "")),
            str(candidate.get("city", "")).lower(),
            str(candidate.get("event_name", "")).lower(),
        ),
    )


def _event_end_date(candidate: dict[str, Any]) -> str | None:
    end_date = candidate.get("end_date")
    if isinstance(end_date, str) and end_date:
        return end_date
    start_date = candidate.get("start_date")
    if isinstance(start_date, str) and start_date:
        return start_date
    return None


def _overlaps_weekend(candidate: dict[str, Any], saturday: str) -> bool:
    try:
        sunday = (
            datetime.date.fromisoformat(saturday) + datetime.timedelta(days=1)
        ).isoformat()
    except ValueError:
        return False

    start_date = candidate.get("start_date")
    end_date = _event_end_date(candidate)
    if not isinstance(start_date, str) or not start_date or end_date is None:
        return False
    return start_date <= sunday and end_date >= saturday


def _find_match_index(
    candidates: list[dict[str, Any]],
    incoming: dict[str, Any],
    target_weekend: str,
) -> int | None:
    incoming_name = _normalize_text(incoming["event_name"])
    incoming_city = _normalize_text(incoming["city"])
    incoming_start = incoming["start_date"]

    for idx, candidate in enumerate(candidates):
        if (
            _normalize_text(str(candidate.get("event_name", ""))) == incoming_name
            and _normalize_text(str(candidate.get("city", ""))) == incoming_city
            and candidate.get("start_date") == incoming_start
        ):
            return idx

    if not _overlaps_weekend(incoming, target_weekend):
        return None

    for idx, candidate in enumerate(candidates):
        if (
            _normalize_text(str(candidate.get("event_name", ""))) == incoming_name
            and _normalize_text(str(candidate.get("city", ""))) == incoming_city
            and _overlaps_weekend(candidate, target_weekend)
        ):
            return idx
    return None


def _merge_candidate(existing: dict[str, Any], incoming: dict[str, Any]) -> dict[str, Any]:
    merged = dict(existing)
    existing_rank = _confidence_rank(existing.get("confidence"))
    incoming_rank = _confidence_rank(incoming.get("confidence"))

    for key, value in incoming.items():
        if key in {"event_name", "city"}:
            continue
        if _has_value(value) and not _has_value(merged.get(key)):
            merged[key] = value

    if incoming_rank > existing_rank:
        for key in STRONG_OVERRIDE_FIELDS:
            if key in incoming:
                merged[key] = incoming.get(key)
        if "confidence" in incoming and _has_value(incoming.get("confidence")):
            merged["confidence"] = incoming["confidence"]
    elif not _has_value(merged.get("confidence")) and _has_value(incoming.get("confidence")):
        merged["confidence"] = incoming["confidence"]

    return merged
