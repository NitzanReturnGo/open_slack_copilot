"""Parse and validate scheduled-prompt job ``metadata.json`` into typed fields."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from common.date_utils import parse_iso_datetime


@dataclass(frozen=True)
class ValidatedScheduledPromptMetadata:
    """Scheduling fields from disk after parse + structural checks."""

    expires_at: datetime
    run_at: datetime | None
    cron: str

    @staticmethod
    def from_dict(meta: dict) -> ValidatedScheduledPromptMetadata:
        expires_at = parse_iso_datetime(meta.get("expires_at"))
        if expires_at is None:
            raise ValueError("missing or invalid expires_at")

        raw_run = (meta.get("run_at") or "").strip()
        if raw_run:
            run_at = parse_iso_datetime(raw_run)
            if run_at is None:
                raise ValueError(f"invalid run_at: {raw_run!r}")
            return ValidatedScheduledPromptMetadata(
                expires_at=expires_at, run_at=run_at, cron="",
            )

        cron = (meta.get("cron") or "").strip()
        if not cron:
            raise ValueError("no run_at and empty cron")
        return ValidatedScheduledPromptMetadata(
            expires_at=expires_at, run_at=None, cron=cron,
        )


def validate_scheduled_prompt_metadata(meta: dict) -> ValidatedScheduledPromptMetadata:
    """Parse ``meta``; raises ``ValueError`` with a short message if invalid."""
    return ValidatedScheduledPromptMetadata.from_dict(meta)
