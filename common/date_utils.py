"""Small helpers for parsing datetimes from stored strings (e.g. metadata JSON)."""

from __future__ import annotations

from datetime import datetime, timezone


def parse_iso_datetime(value: str | None) -> datetime | None:
    """Parse an ISO 8601 datetime string (including trailing ``Z``). Returns ``None`` if empty or invalid."""
    raw = (value or "").strip()
    if not raw:
        return None
    try:
        return datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError:
        return None


def in_past(when: datetime | None) -> bool:
    """True if ``when`` is at or before current UTC time. ``None`` is not in the past."""
    if when is None:
        return False
    return datetime.now(timezone.utc) >= when
