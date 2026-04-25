"""Thread reply as the Slack app (bot). Prepared for future watcher/supervision flows — not registered."""

from __future__ import annotations

from common.slack.slack_api import slack_api
from common.tools.copilot_tool import ToolConfirmationSpec
from common.tools.send_thread_reply_base_tool_helper import build_thread_reply_copilot_tool

_TOOL_NAME = "send_thread_reply_as_app"

SEND_THREAD_REPLY_AS_APP_TOOL, SEND_THREAD_REPLY_AS_APP = build_thread_reply_copilot_tool(
    tool_name=_TOOL_NAME,
    description=(
        "Submit the proposed reply to this thread. The requester must confirm in Slack. "
        "The message is posted in the thread as the app (bot), not as the user."
    ),
    confirmation=ToolConfirmationSpec(
        text_param_key="message",
        ephemeral_notification_text="Confirm app thread reply",
        confirmation_header_markdown=(
            "*Thread reply (as the app)*\n"
            "This will be posted in the thread as the app after you confirm."
        ),
        confirm_button_text="Send thread reply",
    ),
    post=lambda ch, th, body, _pld: slack_api.post_thread_message_as_app(ch, th, body),
)
# Intentionally not register_copilot_tool: opt-in for future skills only.
