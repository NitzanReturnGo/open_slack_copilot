from datetime import datetime, timedelta, timezone

from common.date_utils import in_past, parse_iso_datetime


def test_parse_iso_datetime_z_suffix():
    dt = parse_iso_datetime("2026-04-12T15:30:00Z")
    assert dt == datetime(2026, 4, 12, 15, 30, 0, tzinfo=timezone.utc)


def test_parse_iso_datetime_offset():
    dt = parse_iso_datetime("2026-04-12T12:00:00+00:00")
    assert dt == datetime(2026, 4, 12, 12, 0, 0, tzinfo=timezone.utc)


def test_parse_iso_datetime_empty():
    assert parse_iso_datetime("") is None
    assert parse_iso_datetime(None) is None


def test_parse_iso_datetime_invalid():
    assert parse_iso_datetime("not-a-date") is None


def test_in_past_none():
    assert in_past(None) is False


def test_in_past_future():
    future = datetime.now(timezone.utc) + timedelta(hours=1)
    assert in_past(future) is False


def test_in_past_past():
    past = datetime.now(timezone.utc) - timedelta(seconds=1)
    assert in_past(past) is True
