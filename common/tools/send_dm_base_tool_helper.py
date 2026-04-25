"""Shared send-DM tool wiring (LLM tool + user resolution + confirmation + post hook)."""

from __future__ import annotations

import json
from collections.abc import Callable
from typing import Any

from common.slack.slack_api import slack_api
from common.slack.slack_api.errors import OAuthNotConnectedError
from common.slack.slack_bot.tool_confirmation import queue_tool_confirmation
from common.tools.copilot_tool import (
    TOOL_JSON_STATUS_CONFIRMATION_REQUESTED,
    CopilotTool,
    ToolConfirmationSpec,
)
from common.tools.react_context import get_invocation

PostDmFn = Callable[[str, str, dict[str, Any]], None]


class _ValidationError(Exception):
    pass


def build_send_dm_copilot_tool(
    *,
    tool_name: str,
    description: str,
    confirmation: ToolConfirmationSpec,
    post: PostDmFn,
) -> tuple[dict[str, Any], CopilotTool]:
    llm_schema: dict[str, Any] = {
        "type": "function",
        "function": {
            "name": tool_name,
            "description": description,
            "parameters": {
                "type": "object",
                "properties": {
                    "user": {
                        "type": "string",
                        "description": "Slack user id (U…) from the thread context. Falls back to display name lookup.",
                    },
                    "message": {"type": "string", "description": "DM body"},
                },
                "required": ["user", "message"],
            },
        },
    }

    def _require_str(args: dict, key: str) -> str:
        val = (args.get(key) or "").strip()
        if not val:
            raise _ValidationError(f"{key} is required")
        return val

    def _require_invocation() -> dict:
        inv = get_invocation()
        if not inv:
            raise _ValidationError("Missing invocation context for tool confirmation")
        return inv

    def _resolve_target_user(user: str) -> str:
        uid = slack_api.resolve_user(user)
        if not uid:
            raise _ValidationError(f"Could not resolve user {user!r}")
        return uid

    def _invoke(arguments_json: str) -> str:
        try:
            args = json.loads(arguments_json or "{}")
            user, message = _require_str(args, "user"), _require_str(args, "message")
            uid = _resolve_target_user(user)
            inv = _require_invocation()
        except _ValidationError as e:
            return json.dumps({"error": str(e)})

        result = queue_tool_confirmation(
            tool_name=tool_name,
            text_content=message,
            payload={
                "target_user_id": uid,
                "channel_id": inv["channel_id"],
                "thread_ts": inv.get("thread_ts"),
                "prepare_user_id": inv.get("user_id") or "",
                "context_kind": inv.get("context_kind") or "thread",
            },
            channel_id=inv["channel_id"],
            thread_ts=inv.get("thread_ts"),
            requester_user_id=inv.get("user_id") or "",
        )
        if result.startswith("Error:"):
            return json.dumps({"error": result})
        return json.dumps({"status": TOOL_JSON_STATUS_CONFIRMATION_REQUESTED, "detail": result})

    def _after_confirm(text: str, payload: dict[str, Any]) -> str:
        uid = (payload.get("target_user_id") or "").strip()
        if not uid:
            return "Missing recipient for this action."
        body = (text or "").strip()
        if not body:
            return "Nothing to send."
        try:
            post(uid, body, payload)
        except OAuthNotConnectedError as e:
            return str(e)
        except Exception as e:
            return f"Failed to send: {e}"
        return "Sent."

    tool = CopilotTool(
        name=tool_name,
        llm_schema=llm_schema,
        handle=_invoke,
        confirmation=confirmation,
        execute_after_confirm=_after_confirm,
    )
    return llm_schema, tool
