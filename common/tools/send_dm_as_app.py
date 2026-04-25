"""Send DM as the Slack app (bot). Registered for the default copilot tool set."""

from __future__ import annotations

from common.slack.slack_api import slack_api
from common.tools.copilot_tool import ToolConfirmationSpec, register_copilot_tool
from common.tools.send_dm_base_tool_helper import build_send_dm_copilot_tool

_TOOL_NAME = "send_dm_as_app"

SEND_DM_AS_APP_TOOL, SEND_DM_AS_APP = build_send_dm_copilot_tool(
    tool_name=_TOOL_NAME,
    description=(
        "Queue a direct message to a workspace member. "
        "The requester confirms in Slack; the DM is sent as the app (bot), not as the user."
    ),
    confirmation=ToolConfirmationSpec(
        text_param_key="message",
        ephemeral_notification_text="Confirm DM (app)",
        confirmation_header_markdown=(
            "*Direct message (as the app)*\n"
            "After you confirm, this is sent as a DM from the app to the selected member."
        ),
        confirm_button_text="Send DM",
    ),
    post=lambda uid, body, _pld: slack_api.send_dm(uid, body),
)

register_copilot_tool(SEND_DM_AS_APP)
