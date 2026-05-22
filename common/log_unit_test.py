import logging

import pytest

from common.log import _sanitize, configure_app_logging, resolve_log_level


def test_sanitize_redacts_secrets():
    payload = {
        "token": "secret",
        "response_url": "https://hooks.slack.com/x",
        "channel": {"id": "C1", "name": "general"},
    }
    out = _sanitize(payload)
    assert out["token"] == "<redacted>"
    assert out["response_url"] == "<redacted>"
    assert out["channel"]["id"] == "C1"


def test_sanitize_truncates_long_strings():
    s = "x" * 2000
    out = _sanitize([s])
    assert isinstance(out[0], str)
    assert "truncated" in out[0]
    assert len(out[0]) < len(s)


def test_sanitize_replaces_blocks_with_count():
    msg = {"text": "hi", "blocks": [{"type": "rich_text"}]}
    out = _sanitize(msg)
    assert out["blocks"] == "<1 blocks>"


def test_resolve_log_level_accepts_names_and_ints():
    assert resolve_log_level("INFO") == logging.INFO
    assert resolve_log_level(logging.WARNING) == logging.WARNING


def test_resolve_log_level_rejects_unknown():
    with pytest.raises(ValueError, match="Unknown log level"):
        resolve_log_level("VERBOSE")


def test_configure_app_logging_test_mode_uses_test_level(monkeypatch):
    monkeypatch.setitem(
        __import__("config.config", fromlist=["settings"]).settings,
        "logging",
        {"level": "DEBUG", "test_level": "WARNING"},
    )
    configure_app_logging(test_mode=True)
    from common.log import _logger

    assert _logger.level == logging.WARNING
    configure_app_logging(test_mode=False)
    assert _logger.level == logging.DEBUG


def test_sanitize_caps_long_lists():
    out = _sanitize(list(range(20)), max_list=3)
    assert len(out) == 4
    assert "more items" in out[-1]
