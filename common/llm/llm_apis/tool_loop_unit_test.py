"""Tests for the agent tool loop and ``on_agent_event`` propagation."""

from common.llm.llm_apis.tool_loop import run_agent_tool_loop
from common.llm.llm_apis.types import (
    ChatCompletionTurn,
    NormalizedToolCall,
)


class _FakeBackend:
    def __init__(self, turns: list[ChatCompletionTurn]) -> None:
        self._turns = turns
        self._i = 0

    def complete(self, messages, *, tools=None, tool_choice="auto"):
        if self._i >= len(self._turns):
            return ChatCompletionTurn("", ())
        t = self._turns[self._i]
        self._i += 1
        return t


def test_on_agent_event_emits_tool_then_completion():
    tc = NormalizedToolCall(id="call-1", name="echo", arguments="{}")
    backend = _FakeBackend(
        [
            ChatCompletionTurn("thinking", (tc,)),
            ChatCompletionTurn("final answer", ()),
        ],
    )
    events: list = []

    def run_tool(name: str, arguments_json: str) -> str:
        return '{"status":"ok"}'

    result = run_agent_tool_loop(
        backend,
        "system",
        "user",
        [],
        run_tool,
        on_agent_event=events.append,
    )

    assert result.text == "final answer"
    kinds = [e.kind for e in events]
    assert kinds == [
        "assistant_tool_calls",
        "tool_result",
        "loop_complete",
    ]
    assert events[1].payload["name"] == "echo"
    assert "result_preview" in events[1].payload


def test_on_agent_event_no_tools_single_completion():
    backend = _FakeBackend([ChatCompletionTurn("only text", ())])
    events: list = []

    result = run_agent_tool_loop(
        backend,
        "s",
        "u",
        [],
        lambda n, a: "{}",
        on_agent_event=events.append,
    )

    assert result.text == "only text"
    assert len(events) == 1
    assert events[0].kind == "loop_complete"
    assert events[0].payload["text"] == "only text"
