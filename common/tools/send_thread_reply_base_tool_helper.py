"""Shared send-thread-reply tool wiring (LLM tool + confirmation + post hook)."""

from __future__ import annotations

import json
from collections.abc import Callable
from typing import Any

from common.slack.slack_api.errors import OAuthNotConnectedError
from common.slack.slack_bot.tool_confirmation import queue_tool_confirmation
from common.tools.copilot_tool import (
    TOOL_JSON_STATUS_CONFIRMATION_REQUESTED,
    CopilotTool,
    ToolConfirmationSpec,
)
from common.tools.react_context import get_invocation

PostThreadFn = Callable[[str, str, str, dict[str, Any]], None]


def build_thread_reply_copilot_tool(
    *,
    tool_name: str,
    description: str,
    confirmation: ToolConfirmationSpec,
    post: PostThreadFn,
) -> tuple[dict[str, Any], CopilotTool]:
    llm_schema: dict[str, Any] = {
        "type": "function",
        "function": {
            "name": tool_name,
            "description": description,
            "parameters": {
                "type": "object",
                "properties": {
                    "message": {
                        "type": "string",
                        "description": "Full reply text to post in the thread after confirmation",
                    },
                },
                "required": ["message"],
            },
        },
    }

    def _require_invocation() -> dict:
        inv = get_invocation()
        if not inv:
            raise _ValidationError("Missing invocation context for tool confirmation")
        return inv

    def _require_str(args: dict, key: str) -> str:
        val = (args.get(key) or "").strip()
        if not val:
            raise _ValidationError(f"{key} is required")
        return val

    def _invoke(arguments_json: str) -> str:
        try:
            args = json.loads(arguments_json or "{}")
            message = _require_str(args, "message")
            inv = _require_invocation()
        except _ValidationError as e:
            return json.dumps({"error": str(e)})

        thread_ts = (inv.get("thread_ts") or "").strip()
        channel_id = (inv.get("channel_id") or "").strip()
        if not thread_ts or not channel_id:
            return json.dumps({"error": "Missing channel or thread anchor for thread reply"})

        payload: dict[str, Any] = {
            "channel_id": channel_id,
            "thread_ts": thread_ts,
            "prepare_user_id": inv.get("user_id") or "",
            "context_kind": inv.get("context_kind") or "thread",
        }
        result = queue_tool_confirmation(
            tool_name=tool_name,
            text_content=message,
            payload=payload,
            channel_id=channel_id,
            thread_ts=thread_ts,
            requester_user_id=inv.get("user_id") or "",
        )
        if result.startswith("Error:"):
            return json.dumps({"error": result})
        return json.dumps({"status": TOOL_JSON_STATUS_CONFIRMATION_REQUESTED, "detail": result})

    def _after_confirm(text: str, pld: dict[str, Any]) -> str:
        channel_id = (pld.get("channel_id") or "").strip()
        thread_ts = (pld.get("thread_ts") or "").strip()
        if not channel_id or not thread_ts:
            return "Missing channel or thread for this action."
        body = (text or "").strip()
        if not body:
            return "Nothing to post."
        try:
            post(channel_id, thread_ts, body, pld)
        except OAuthNotConnectedError as e:
            return str(e)
        except Exception as e:
            return f"Failed to post: {e}"
        return "Posted to thread."

    tool = CopilotTool(
        name=tool_name,
        llm_schema=llm_schema,
        handle=_invoke,
        confirmation=confirmation,
        execute_after_confirm=_after_confirm,
    )
    return llm_schema, tool


class _ValidationError(Exception):
    pass
