from datetime import datetime, timedelta, timezone

import pytest

from common.tools.prompt_scheduler.scheduled_prompt_metadata import (
    validate_scheduled_prompt_metadata,
)


def _now():
    return datetime.now(timezone.utc)


def test_validate_cron_schedule():
    now = _now()
    meta = {
        "expires_at": (now + timedelta(days=7)).isoformat().replace("+00:00", "Z"),
        "cron": "  0 9 * * *  ",
    }
    v = validate_scheduled_prompt_metadata(meta)
    assert v.run_at is None
    assert v.cron == "0 9 * * *"


def test_validate_run_at_schedule():
    now = _now()
    run_at = (now + timedelta(hours=1)).isoformat().replace("+00:00", "Z")
    meta = {
        "expires_at": (now + timedelta(days=7)).isoformat().replace("+00:00", "Z"),
        "run_at": run_at,
        "cron": "",
    }
    v = validate_scheduled_prompt_metadata(meta)
    assert v.run_at is not None
    assert v.cron == ""


def test_validate_missing_expires_at():
    with pytest.raises(ValueError, match="expires_at"):
        validate_scheduled_prompt_metadata({"cron": "0 9 * * *"})


def test_validate_invalid_run_at():
    now = _now()
    with pytest.raises(ValueError, match="invalid run_at"):
        validate_scheduled_prompt_metadata(
            {
                "expires_at": (now + timedelta(days=1)).isoformat().replace("+00:00", "Z"),
                "run_at": "bogus",
            }
        )


def test_validate_empty_cron_without_run_at():
    now = _now()
    with pytest.raises(ValueError, match="empty cron"):
        validate_scheduled_prompt_metadata(
            {
                "expires_at": (now + timedelta(days=1)).isoformat().replace("+00:00", "Z"),
                "cron": "   ",
            }
        )
