"""Send DM on behalf of the requester (user OAuth). Prepared for future flows — not registered."""

from __future__ import annotations

from common.slack.slack_api import slack_api
from common.tools.copilot_tool import ToolConfirmationSpec
from common.tools.send_dm_base_tool_helper import build_send_dm_copilot_tool

_TOOL_NAME = "send_dm_on_behalf_of_requester"

SEND_DM_ON_BEHALF_OF_REQUESTER_TOOL, SEND_DM_ON_BEHALF_OF_REQUESTER = build_send_dm_copilot_tool(
    tool_name=_TOOL_NAME,
    description=(
        "Queue a direct message to a workspace member. "
        "The requester confirms in Slack; the DM is sent in their name (user OAuth), not as the app."
    ),
    confirmation=ToolConfirmationSpec(
        text_param_key="message",
        ephemeral_notification_text="Confirm DM (on your behalf)",
        confirmation_header_markdown=(
            "*Direct message (on your behalf)*\n"
            "After you confirm, this is sent as a DM from you to the selected member (user OAuth), not as the app."
        ),
        confirm_button_text="Send DM",
    ),
    post=lambda uid, body, pld: slack_api.send_dm_on_behalf_of_requester(
        (pld.get("prepare_user_id") or "").strip(), uid, body,
    ),
)
