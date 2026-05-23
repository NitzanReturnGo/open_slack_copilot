"""End-to-end: confirm ``send_thread_reply_on_behalf_of_requester`` posts via SLACK_USER_TOKEN.

Exercises the real ``oauth_token_store`` + ``slack_api.post_thread_message_on_behalf_of_requester``
path (not a mocked ``slack_api`` on the tool module). When the requester matches the token owner
from ``auth.test``, confirm should post without per-user OAuth rows.

Run: ``pytest tests/e2e_use_cases/on_behalf_slack_user_token_end_to_end_test.py -v -s``
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

import common.tools.send_thread_reply_on_behalf_of_requester  # noqa: F401 — registers tool
from common.data_layer import data_layer
from common.log import get_test_logger
from common.slack.slack_api import oauth_token_store
from common.slack.slack_bot import tool_confirmation as tc

C_TEST = "C0ALHSXRDU5"
U_OWNER = "U0AMFJ2AVME"
U_OTHER = "U0ALHV1GDDK"
TS_ROOT = "1779470715.457809"
DRAFT_TEXT = (
    "Hi <@U0ALHV1GDDK>, when you have a moment, could you please test your open tasks? "
    "Thank you!"
)
OWNER_TOKEN = "xoxp-e2e-owner-token"

_e2e_log = get_test_logger("e2e")


def _log(msg: str) -> None:
    _e2e_log.info("[e2e] %s", msg)


def _log_ok(label: str) -> None:
    _e2e_log.info("[e2e] ok: %s", label)


def _confirm_action_body(confirm_value: str, *, user_id: str = U_OWNER) -> dict[str, Any]:
    return {
        "user": {"id": user_id},
        "channel": {"id": C_TEST},
        "actions": [{"value": confirm_value, "action_id": tc.ACTION_TOOL_CONFIRM}],
        "container": {"thread_ts": TS_ROOT},
        "message": {"blocks": []},
    }


def _build_confirm_value(
    *,
    requester_user_id: str,
    draft_text: str = DRAFT_TEXT,
) -> str:
    payload = {
        "channel_id": C_TEST,
        "thread_ts": TS_ROOT,
        "prepare_user_id": requester_user_id,
        "context_kind": "thread",
    }
    meta = {
        "v": 1,
        "tool_name": "send_thread_reply_on_behalf_of_requester",
        "payload": payload,
        "draft_ref": tc._save_draft(draft_text),
    }
    return json.dumps(meta, separators=(",", ":"))


@pytest.fixture
def isolated_oauth_store(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """No saved per-user tokens; only env-based owner fallback is available."""
    monkeypatch.setattr(data_layer, "_data_root", lambda: tmp_path)
    monkeypatch.setattr(oauth_token_store, "_owner_user_id_cache", None)
    drafts = tmp_path / "tool_confirm_drafts"
    drafts.mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr(tc, "_TOOL_CONFIRM_DRAFT_DIR", drafts)


def _patch_webclient_recording() -> tuple[list[MagicMock], Any]:
    """Return (clients, patcher context) that records WebClient(token=...) used for on-behalf post."""
    clients: list[MagicMock] = []

    def _factory(token: str, ssl: object | None = None) -> MagicMock:
        client = MagicMock(name=f"WebClient({token[:12]}…)")
        client.token = token
        clients.append(client)
        return client

    return clients, patch("common.slack.slack_api.slack_api.WebClient", side_effect=_factory)


class TestOnBehalfSlackUserTokenEndToEnd:
    def test_confirm_posts_thread_reply_using_slack_user_token_for_owner(
        self, isolated_oauth_store: None, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.setenv("SLACK_USER_TOKEN", OWNER_TOKEN)
        monkeypatch.setattr(
            oauth_token_store, "_resolve_owner_user_id", lambda _t: U_OWNER,
        )

        clients, webclient_patch = _patch_webclient_recording()
        with webclient_patch:
            confirm_value = _build_confirm_value(requester_user_id=U_OWNER)
            result = tc.handle_confirm_action(_confirm_action_body(confirm_value))

        assert result == "Posted to thread.", result
        assert oauth_token_store.get_user_token(U_OWNER) == OWNER_TOKEN
        assert len(clients) == 1
        assert clients[0].token == OWNER_TOKEN
        clients[0].chat_postMessage.assert_called_once_with(
            channel=C_TEST,
            thread_ts=TS_ROOT,
            text=DRAFT_TEXT,
            mrkdwn=True,
        )
        _log_ok("on-behalf post via SLACK_USER_TOKEN")

    def test_confirm_returns_oauth_error_when_no_token_for_requester(
        self, isolated_oauth_store: None, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.delenv("SLACK_USER_TOKEN", raising=False)
        monkeypatch.setattr(
            oauth_token_store, "_resolve_owner_user_id", lambda _t: U_OWNER,
        )

        clients, webclient_patch = _patch_webclient_recording()
        with webclient_patch:
            confirm_value = _build_confirm_value(requester_user_id=U_OWNER)
            result = tc.handle_confirm_action(_confirm_action_body(confirm_value))

        assert "No OAuth is connected" in result
        assert oauth_token_store.get_user_token(U_OWNER) is None
        assert clients == []
        _log_ok("OAuth error without SLACK_USER_TOKEN")

    def test_confirm_oauth_error_when_requester_is_not_token_owner(
        self, isolated_oauth_store: None, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.setenv("SLACK_USER_TOKEN", OWNER_TOKEN)
        monkeypatch.setattr(
            oauth_token_store, "_resolve_owner_user_id", lambda _t: U_OWNER,
        )

        clients, webclient_patch = _patch_webclient_recording()
        with webclient_patch:
            confirm_value = _build_confirm_value(requester_user_id=U_OTHER)
            result = tc.handle_confirm_action(
                _confirm_action_body(confirm_value, user_id=U_OTHER),
            )

        assert "No OAuth is connected" in result
        assert oauth_token_store.get_user_token(U_OTHER) is None
        assert clients == []
        _log_ok("OAuth error for non-owner requester")
