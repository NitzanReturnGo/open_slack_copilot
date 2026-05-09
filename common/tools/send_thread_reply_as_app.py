"""Thread reply as the Slack app (bot). Used by skills that post automated reminders/notifications in-thread."""

from __future__ import annotations

from common.slack.slack_api import slack_api
from common.tools.copilot_tool import ToolConfirmationSpec, register_copilot_tool
from common.tools.send_thread_reply_base_tool_helper import build_thread_reply_copilot_tool

_TOOL_NAME = "send_thread_reply_as_app"

SEND_THREAD_REPLY_AS_APP_TOOL, SEND_THREAD_REPLY_AS_APP = build_thread_reply_copilot_tool(
    tool_name=_TOOL_NAME,
    description=(
        "Reminder/notification tool. Posts in the thread as the app (bot), not as a person. "
        "Use ONLY for automated reminders, nudges, or system notices that the bot itself is "
        "announcing — never for messages a person would author."
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
register_copilot_tool(SEND_THREAD_REPLY_AS_APP)
