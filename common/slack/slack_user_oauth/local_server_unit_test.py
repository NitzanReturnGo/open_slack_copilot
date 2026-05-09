import threading
from http.client import HTTPConnection
from http.server import HTTPServer

import pytest

from common.slack.slack_api import oauth_token_store
from common.slack.slack_user_oauth import local_server
from common.slack.slack_user_oauth.local_server import (
    SlackUserOAuthHandler,
    _issue_state,
    build_authorize_url,
)

_FAKE_USER_ID = "U_FAKE_TEST_OAUTH_USER"


def test_build_authorize_url_encodes_params():
    url = build_authorize_url(
        client_id="C123.456",
        user_scopes=["chat:write"],
        redirect_uri="http://127.0.0.1:8765/slack/oauth/callback",
        state="abc",
    )
    assert url.startswith("https://slack.com/oauth/v2/authorize?")
    assert "client_id=C123.456" in url or "client_id=C123%2E456" in url
    assert "user_scope=chat%3Awrite" in url
    assert "state=abc" in url
    assert "redirect_uri=" in url


@pytest.fixture
def server():
    httpd = HTTPServer(("127.0.0.1", 0), SlackUserOAuthHandler)
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    host, port = httpd.server_address
    try:
        yield f"{host}:{port}"
    finally:
        httpd.shutdown()
        httpd.server_close()
        thread.join(timeout=2)


def _get(addr: str, path: str) -> tuple[int, str]:
    conn = HTTPConnection(addr, timeout=5)
    conn.request("GET", path)
    resp = conn.getresponse()
    body = resp.read().decode("utf-8", errors="replace")
    conn.close()
    return resp.status, body


def test_callback_success_saves_fake_user_token(server, monkeypatch):
    saved: dict = {}

    def fake_exchange(*, client_id, client_secret, code, redirect_uri):
        return _FAKE_USER_ID, "xoxp-fake-token", ["chat:write"]

    def fake_save(user_id, token, *, scopes=None):
        assert user_id == _FAKE_USER_ID, "test must not write real user ids"
        saved["user_id"] = user_id
        saved["token"] = token
        saved["scopes"] = scopes

    monkeypatch.setattr(local_server, "exchange_user_oauth_code", fake_exchange)
    monkeypatch.setattr(oauth_token_store, "save_user_token", fake_save)

    state = _issue_state()
    status, body = _get(server, f"/slack/oauth/callback?code=abc&state={state}")

    assert status == 200
    assert _FAKE_USER_ID in body
    assert saved == {
        "user_id": _FAKE_USER_ID,
        "token": "xoxp-fake-token",
        "scopes": ["chat:write"],
    }


def test_callback_invalid_state_returns_400(server):
    status, body = _get(server, "/slack/oauth/callback?code=abc&state=not-a-real-state")
    assert status == 400
    assert "invalid OAuth state" in body or "Missing or invalid" in body


def test_callback_slack_error_returns_400(server):
    status, body = _get(server, "/slack/oauth/callback?error=access_denied")
    assert status == 400
    assert "access_denied" in body
