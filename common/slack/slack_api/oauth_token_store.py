"""Persist Slack user OAuth tokens under the data layer (one JSON file per user)."""

from __future__ import annotations

import time
from typing import Any

from common.data_layer import get_collection

_COLLECTION_NAME = "slack_user_oauth"


def _col() -> Any:
    return get_collection(_COLLECTION_NAME)


def get_user_token(user_id: str) -> str | None:
    uid = (user_id or "").strip()
    if not uid:
        return None
    row = _col().get(uid)
    if not row:
        return None
    t = (row.get("token") or "").strip()
    return t or None


def save_user_token(
    user_id: str,
    token: str,
    *,
    scopes: list[str] | None = None,
) -> None:
    uid = (user_id or "").strip()
    if not uid:
        raise ValueError("user_id is required")
    payload: dict[str, Any] = {
        "token": (token or "").strip(),
        "saved_at": time.time(),
    }
    if scopes is not None:
        payload["scopes"] = list(scopes)
    _col().set(uid, payload)
