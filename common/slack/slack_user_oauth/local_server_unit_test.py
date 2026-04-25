from common.slack.slack_user_oauth.local_server import build_authorize_url


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
