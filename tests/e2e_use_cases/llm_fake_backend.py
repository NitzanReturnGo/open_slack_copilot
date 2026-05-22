"""Fake LLM completion backend for e2e tests; counts input tokens with tiktoken."""

from __future__ import annotations

from typing import Any

import tiktoken

from common.llm.llm_apis.types import ChatCompletionTurn

# ~4% headroom above follow-up e2e peak (1633); measured with pytest -s token logs.
MAX_INPUT_TOKENS_PER_COMPLETION = 1700

_ENCODING = tiktoken.encoding_for_model("gpt-4o")


def _count_input_tokens(messages: list[dict[str, Any]]) -> int:
    total = 0
    for msg in messages:
        content = msg.get("content")
        if isinstance(content, str) and content:
            total += len(_ENCODING.encode(content))
    return total


class FakeCompletionBackend:
    def __init__(self, turns: list[ChatCompletionTurn]):
        self._turns = list(turns)
        self.complete_calls: list[list[dict[str, Any]]] = []
        self.input_token_counts: list[int] = []

    def complete(
        self,
        messages: list[dict[str, Any]],
        *,
        tools: list[dict[str, Any]] | None = None,
        tool_choice: str = "auto",
    ) -> ChatCompletionTurn:
        self.complete_calls.append(list(messages))
        self.input_token_counts.append(_count_input_tokens(messages))
        if not self._turns:
            raise AssertionError("FakeCompletionBackend: no scripted turns left")
        return self._turns.pop(0)


def assert_llm_input_token_budget(
    fake_backend: FakeCompletionBackend,
    *,
    max_tokens: int = MAX_INPUT_TOKENS_PER_COMPLETION,
    log_ok: Any | None = None,
    log_info: Any | None = None,
) -> None:
    counts = fake_backend.input_token_counts
    peak = max(counts) if counts else 0
    if log_info is not None:
        for i, count in enumerate(counts):
            log_info(f"LLM complete call {i}: input_tokens={count}")
        log_info(f"LLM input_tokens peak={peak} cap={max_tokens}")
    for count in counts:
        assert count <= max_tokens, (
            f"LLM input tokens {count} exceed max {max_tokens} per completion"
        )
    if log_ok is not None:
        log_ok("prompt token limits")
