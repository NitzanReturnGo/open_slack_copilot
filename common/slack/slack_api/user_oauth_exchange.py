"""Exchange a Slack OAuth v2 authorization code for a user (xoxp-) token."""

from __future__ import annotations

import ssl
from typing import Any

import certifi
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError


def _ssl_context() -> ssl.SSLContext:
    return ssl.create_default_context(cafile=certifi.where())


def parse_oauth_v2_user_credentials(body: dict[str, Any]) -> tuple[str, str, list[str]]:
    """
    Parse ``oauth.v2.access`` JSON for a user-token-only install.

    Returns:
        ``(slack_user_id, user_access_token, user_scope_list)``
    """
    if not body.get("ok"):
        err = body.get("error", "unknown_error")
        raise ValueError(f"oauth.v2.access failed: {err}")
    au = body.get("authed_user") or {}
    token = (au.get("access_token") or "").strip()
    user_id = (au.get("id") or "").strip()
    scope_str = (au.get("scope") or "").strip()
    scopes = [s.strip() for s in scope_str.split(",") if s.strip()] if scope_str else []
    if not token or not user_id:
        raise ValueError(
            "Slack did not return a user OAuth token. "
            "Ensure the authorize URL includes user_scope (e.g. chat:write) and the app allows user scopes."
        )
    return user_id, token, scopes


def exchange_user_oauth_code(
    *,
    client_id: str,
    client_secret: str,
    code: str,
    redirect_uri: str,
) -> tuple[str, str, list[str]]:
    """Call ``oauth.v2.access`` and return user id, user token, and user scopes."""
    cid = (client_id or "").strip()
    sec = (client_secret or "").strip()
    c = (code or "").strip()
    redir = (redirect_uri or "").strip()
    if not cid or not sec:
        raise ValueError("client_id and client_secret are required")
    if not c:
        raise ValueError("code is required")
    if not redir:
        raise ValueError("redirect_uri is required")
    client = WebClient(ssl=_ssl_context())
    try:
        resp = client.oauth_v2_access(
            client_id=cid,
            client_secret=sec,
            code=c,
            redirect_uri=redir,
        )
    except SlackApiError as e:
        raise ValueError(str(e)) from e
    body = {
        "ok": resp.get("ok"),
        "error": resp.get("error"),
        "authed_user": resp.get("authed_user") or {},
    }
    return parse_oauth_v2_user_credentials(body)
