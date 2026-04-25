"""Thread reply on behalf of the requester (user OAuth). Registered for the default copilot tool set."""

from __future__ import annotations

from common.slack.slack_api import slack_api
from common.tools.copilot_tool import ToolConfirmationSpec, register_copilot_tool
from common.tools.send_thread_reply_base_tool_helper import build_thread_reply_copilot_tool

_TOOL_NAME = "send_thread_reply_on_behalf_of_requester"

SEND_THREAD_REPLY_ON_BEHALF_OF_REQUESTER_TOOL, _TOOL = build_thread_reply_copilot_tool(
    tool_name=_TOOL_NAME,
    description=(
        "Submit the proposed reply to this thread. The requester must confirm in Slack. "
        "The message is posted in the thread on behalf of the requester (user OAuth), not as the app."
    ),
    confirmation=ToolConfirmationSpec(
        text_param_key="message",
        ephemeral_notification_text="Confirm thread reply",
        confirmation_header_markdown=(
            "*Thread reply (on your behalf)*\n"
            "This will be posted in the thread on your behalf after you confirm."
        ),
        confirm_button_text="Send thread reply",
    ),
    post=lambda ch, th, body, pld: slack_api.post_thread_message_on_behalf_of_requester(
        ch, th, body, (pld.get("prepare_user_id") or "").strip(),
    ),
)

SEND_THREAD_REPLY_ON_BEHALF_OF_REQUESTER = _TOOL
register_copilot_tool(SEND_THREAD_REPLY_ON_BEHALF_OF_REQUESTER)
