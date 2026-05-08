import json
from unittest.mock import patch

from common.tools.react_context import react_invocation_context
from common.tools.send_ephemeral_message import (
    SEND_EPHEMERAL_MESSAGE,
    SEND_EPHEMERAL_MESSAGE_TOOL,
)


def test_tool_schema_name():
    assert SEND_EPHEMERAL_MESSAGE_TOOL["type"] == "function"
    assert SEND_EPHEMERAL_MESSAGE_TOOL["function"]["name"] == "send_ephemeral_message"
    params = SEND_EPHEMERAL_MESSAGE_TOOL["function"]["parameters"]
    assert set(params["required"]) == {"user", "message"}


@patch("common.tools.send_ephemeral_message.slack_api")
def test_handle_sends_ephemeral_truncates_long_message(mock_api):
    mock_api.resolve_user.return_value = "U99"
    mock_api.get_user_display_name.return_value = ""
    long_body = "x" * 600
    with react_invocation_context("C1", "T1.0", "Ureq"):
        out = json.loads(
            SEND_EPHEMERAL_MESSAGE.handle(
                json.dumps({"user": "U99", "message": long_body})
            )
        )
    assert out.get("status") == "sent"
    msg = out.get("message", "")
    assert msg.startswith("To U99:")
    assert len(msg) < len(long_body) + 20
    assert msg.endswith("…")


def test_handle_requires_invocation_context():
    out = json.loads(
        SEND_EPHEMERAL_MESSAGE.handle(json.dumps({"user": "U0123456789", "message": "hi"}))
    )
    assert "error" in out


@patch("common.tools.send_ephemeral_message.slack_api")
def test_handle_sends_ephemeral(mock_api):
    mock_api.resolve_user.return_value = "U99"
    mock_api.get_user_display_name.return_value = "Alex"
    with react_invocation_context("C1", "T1.0", "Ureq"):
        out = json.loads(
            SEND_EPHEMERAL_MESSAGE.handle(
                json.dumps({"user": "someone", "message": "please review"})
            )
        )
    assert out.get("status") == "sent"
    assert out.get("message") == "To Alex: please review"
    mock_api.send_ephemeral.assert_called_once_with(
        "C1", "T1.0", "U99", "please review",
    )
