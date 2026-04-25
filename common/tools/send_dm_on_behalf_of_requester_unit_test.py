from unittest.mock import patch

import common.tools.send_dm_as_app  # noqa: F401 — ensure as-app import path doesn't break
from common.slack.slack_api.errors import OAuthNotConnectedError
from common.tools.copilot_tool import get_copilot_tool
from common.tools.send_dm_on_behalf_of_requester import (
    SEND_DM_ON_BEHALF_OF_REQUESTER,
    SEND_DM_ON_BEHALF_OF_REQUESTER_TOOL,
)


def test_tool_built_not_registered():
    assert SEND_DM_ON_BEHALF_OF_REQUESTER_TOOL["function"]["name"] == "send_dm_on_behalf_of_requester"
    assert get_copilot_tool("send_dm_on_behalf_of_requester") is None
    assert SEND_DM_ON_BEHALF_OF_REQUESTER.name == "send_dm_on_behalf_of_requester"
    assert SEND_DM_ON_BEHALF_OF_REQUESTER.execute_after_confirm is not None


def test_execute_after_confirm_posts():
    with patch("common.tools.send_dm_on_behalf_of_requester.slack_api") as api:
        out = SEND_DM_ON_BEHALF_OF_REQUESTER.execute_after_confirm(
            "body",
            {
                "target_user_id": "U_T",
                "channel_id": "C1",
                "thread_ts": "1.0",
                "prepare_user_id": "U_REQ",
            },
        )
    assert out == "Sent."
    api.send_dm_on_behalf_of_requester.assert_called_once_with("U_REQ", "U_T", "body")


def test_execute_after_confirm_oauth_missing_message():
    with patch("common.tools.send_dm_on_behalf_of_requester.slack_api") as api:
        api.send_dm_on_behalf_of_requester.side_effect = OAuthNotConnectedError("U_REQ")
        out = SEND_DM_ON_BEHALF_OF_REQUESTER.execute_after_confirm(
            "body",
            {
                "target_user_id": "U_T",
                "channel_id": "C1",
                "thread_ts": "1.0",
                "prepare_user_id": "U_REQ",
            },
        )
    assert "No OAuth" in out
