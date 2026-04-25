"""Minimal HTTP server for Slack user OAuth v2 callback (private / localhost testing)."""

from __future__ import annotations

import secrets
import time
from http.server import BaseHTTPRequestHandler, HTTPServer
from typing import Any
from urllib.parse import parse_qs, quote, urlencode, urlparse

from common.log import log
from common.slack.slack_api import oauth_token_store
from common.slack.slack_api.user_oauth_exchange import exchange_user_oauth_code

_STATE_TTL_SEC = 600
_states: dict[str, float] = {}


def _purge_expired_states() -> None:
    now = time.time()
    for s, t in list(_states.items()):
        if now - t > _STATE_TTL_SEC:
            del _states[s]


def _issue_state() -> str:
    _purge_expired_states()
    s = secrets.token_urlsafe(24)
    _states[s] = time.time()
    return s


def _consume_state(state: str) -> bool:
    _purge_expired_states()
    if not state or state not in _states:
        return False
    del _states[state]
    return True


def _user_oauth_settings() -> dict[str, Any]:
    from config.config import settings

    raw = settings.slack_bot.get("user_oauth") or {}
    return dict(raw) if isinstance(raw, dict) else {}


def effective_redirect_uri() -> str:
    import os

    override = (os.environ.get("SLACK_USER_OAUTH_REDIRECT_URI") or "").strip()
    if override:
        return override
    uo = _user_oauth_settings()
    return (uo.get("redirect_uri") or "http://127.0.0.1:8765/slack/oauth/callback").strip()


def build_authorize_url(*, client_id: str, user_scopes: list[str], redirect_uri: str, state: str) -> str:
    cid = (client_id or "").strip()
    if not cid:
        raise ValueError("client_id is required")
    scopes = ",".join(s.strip() for s in user_scopes if (s or "").strip())
    if not scopes:
        raise ValueError("user_scopes must be non-empty")
    q = urlencode(
        {
            "client_id": cid,
            "user_scope": scopes,
            "redirect_uri": redirect_uri,
            "state": state,
        },
        quote_via=quote,
    )
    return f"https://slack.com/oauth/v2/authorize?{q}"


def _html_page(title: str, body: str, status: int = 200) -> tuple[int, str, bytes]:
    html = (
        f"<!DOCTYPE html><html><head><meta charset=\"utf-8\"/><title>{title}</title></head>"
        f"<body><p>{body}</p></body></html>"
    )
    data = html.encode("utf-8")
    return status, "text/html; charset=utf-8", data


class SlackUserOAuthHandler(BaseHTTPRequestHandler):
    server_version = "OpenSlackCopilotUserOAuth/1.0"

    def log_message(self, fmt: str, *args: Any) -> None:
        # Quiet default stderr logging; use common.log where needed.
        pass

    def do_GET(self) -> None:  # noqa: N802 — stdlib name
        parsed = urlparse(self.path)
        path = parsed.path.rstrip("/") or "/"
        qs = parse_qs(parsed.query or "")

        if path == "/slack/oauth/start":
            self._handle_start()
            return
        if path == "/slack/oauth/callback":
            self._handle_callback(qs)
            return
        if path in ("/", "/health"):
            msg = "User OAuth server. Open /slack/oauth/start to connect your Slack user."
            status, ctype, body = _html_page("Slack user OAuth", msg)
            self._send(status, ctype, body)
            return
        self.send_error(404, "Not found")

    def _send(self, status: int, content_type: str, body: bytes) -> None:
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _handle_start(self) -> None:
        uo = _user_oauth_settings()
        client_id = (uo.get("client_id") or "").strip()
        if not client_id:
            status, ctype, body = _html_page(
                "Configuration error",
                "Set SLACK_CLIENT_ID (and SLACK_CLIENT_SECRET) in .env for this server.",
                status=500,
            )
            self._send(status, ctype, body)
            return
        raw_scopes = uo.get("user_scopes") or ["chat:write"]
        if isinstance(raw_scopes, (list, tuple)):
            user_scopes = [str(s) for s in raw_scopes]
        else:
            user_scopes = ["chat:write"]
        try:
            state = _issue_state()
            url = build_authorize_url(
                client_id=client_id,
                user_scopes=user_scopes,
                redirect_uri=effective_redirect_uri(),
                state=state,
            )
        except ValueError as e:
            status, ctype, body = _html_page("Configuration error", str(e), status=500)
            self._send(status, ctype, body)
            return
        self.send_response(302)
        self.send_header("Location", url)
        self.end_headers()

    def _handle_callback(self, qs: dict[str, list[str]]) -> None:
        def _one(key: str) -> str:
            v = qs.get(key) or []
            return (v[0] if v else "").strip()

        code = _one("code")
        state = _one("state")
        err = _one("error")

        if err:
            status, ctype, body = _html_page(
                "Slack OAuth",
                f"Slack returned an error: {err}",
                status=400,
            )
            self._send(status, ctype, body)
            return
        if not code or not _consume_state(state):
            status, ctype, body = _html_page(
                "Slack OAuth",
                "Missing or invalid OAuth state. Open /slack/oauth/start again and retry.",
                status=400,
            )
            self._send(status, ctype, body)
            return

        uo = _user_oauth_settings()
        client_id = (uo.get("client_id") or "").strip()
        client_secret = (uo.get("client_secret") or "").strip()
        redirect_uri = effective_redirect_uri()

        try:
            user_id, token, scopes = exchange_user_oauth_code(
                client_id=client_id,
                client_secret=client_secret,
                code=code,
                redirect_uri=redirect_uri,
            )
            oauth_token_store.save_user_token(user_id, token, scopes=scopes)
        except ValueError as e:
            status, ctype, body = _html_page("OAuth failed", str(e), status=400)
            self._send(status, ctype, body)
            return

        status, ctype, body = _html_page(
            "Slack connected",
            f"Stored user OAuth token for Slack user <code>{user_id}</code>. You can close this tab.",
        )
        self._send(status, ctype, body)


@log
def run_user_oauth_server() -> None:
    """Bind HTTP server from ``slack_bot.user_oauth`` settings and serve until interrupted."""
    uo = _user_oauth_settings()
    host = (uo.get("bind_host") or "127.0.0.1").strip()
    port = int(uo.get("bind_port") or 8765)
    client_id = (uo.get("client_id") or "").strip()
    client_secret = (uo.get("client_secret") or "").strip()
    if not client_id or not client_secret:
        raise SystemExit(
            "SLACK_CLIENT_ID and SLACK_CLIENT_SECRET must be set in the environment (.env) "
            "to run the user OAuth server (Slack app → Basic Information)."
        )
    redir = effective_redirect_uri()
    httpd = HTTPServer((host, port), SlackUserOAuthHandler)
    print(  # noqa: T201 — CLI entry
        f"User OAuth server listening on http://{host}:{port}\n"
        f"- Add this Redirect URL in Slack: {redir}\n"
        f"- Open http://{host}:{port}/slack/oauth/start in your browser to connect.\n"
        "Press Ctrl+C to stop."
    )
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down.")  # noqa: T201
    finally:
        httpd.server_close()
