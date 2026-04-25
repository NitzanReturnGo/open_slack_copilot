import pytest

from common.slack.slack_api.user_oauth_exchange import (
    parse_oauth_v2_user_credentials,
)


def test_parse_success():
    uid, tok, scopes = parse_oauth_v2_user_credentials(
        {
            "ok": True,
            "authed_user": {
                "id": "U123",
                "access_token": "xoxp-secret",
                "scope": "chat:write,channels:read",
            },
        }
    )
    assert uid == "U123"
    assert tok == "xoxp-secret"
    assert scopes == ["chat:write", "channels:read"]


def test_parse_single_scope():
    _, _, scopes = parse_oauth_v2_user_credentials(
        {
            "ok": True,
            "authed_user": {"id": "U1", "access_token": "xoxp-a", "scope": "chat:write"},
        }
    )
    assert scopes == ["chat:write"]


def test_parse_not_ok():
    with pytest.raises(ValueError, match="oauth.v2.access failed"):
        parse_oauth_v2_user_credentials({"ok": False, "error": "bad_code"})


def test_parse_missing_user_token():
    with pytest.raises(ValueError, match="user OAuth token"):
        parse_oauth_v2_user_credentials({"ok": True, "authed_user": {}})
