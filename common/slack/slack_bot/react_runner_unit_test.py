import pytest
from unittest.mock import MagicMock, patch

from common.llm.llm_apis.types import ToolCallRecord
from common.slack.copilot_pipeline import ReactLoopResult
from common.slack.slack_bot import react_runner as rr
from common.slack.slack_bot.react_runner import ReviseError, _format_failure_message


@pytest.mark.parametrize(
    ("trigger", "action", "expected"),
    [
        (None, None, "Failed to process request."),
        ("", "  ", "Failed to process request."),
        ("slash", None, "Failed to process: slash."),
        (None, "act", "Failed to process: act."),
        ("t1", "a1", "Failed to process: t1, a1."),
    ],
)
def test_format_failure_message(trigger, action, expected):
    assert _format_failure_message(trigger, action) == expected


def test_resolve_missing_anchor_channel_tail_ok():
    from common.slack.slack_bot.react_runner import _resolve_thread_messages
    from unittest.mock import patch

    with patch(
        "common.slack.slack_bot.react_runner.fetch_channel_tail_messages",
        return_value=[{"ts": "1"}],
    ) as mock_tail:
        out = _resolve_thread_messages(
            "C1", "", "channel_tail", None,
        )
    assert out == [{"ts": "1"}]
    mock_tail.assert_called_once_with("C1")


def test_resolve_missing_anchor_thread_raises():
    from common.slack.slack_bot.react_runner import _resolve_thread_messages

    with pytest.raises(ReviseError, match="Missing thread anchor"):
        _resolve_thread_messages("C1", "", "thread", None)


def test_build_notify_mode_receipt_schedule_prompt():
    trace = [
        ToolCallRecord(
            "schedule_prompt",
            '{"status":"scheduled","job_id":"sched_abc","message":"Prompt scheduled with cron \'0 9 * * *\'; expires in 14 days."}',
        ),
    ]
    body = rr._build_notify_mode_receipt(trace)
    assert "Scheduled prompt" in body
    assert "Prompt scheduled" in body


def test_post_loop_confirm_pending_still_sends_notify_receipt():
    loop_out = ReactLoopResult(
        "",
        [
            ToolCallRecord(
                "schedule_prompt",
                '{"status":"scheduled","job_id":"j1","message":"ok"}',
            ),
            ToolCallRecord("send_thread_reply_on_behalf_of_requester", '{"status":"tool_confirmation_requested"}'),
        ],
        [],
    )
    mock_notify = MagicMock()
    with patch.object(rr, "copilot_user_notify", mock_notify):
        rr._post_loop_ephemeral("C1", "T1", "U1", loop_out)
    mock_notify.notify_react_feedback.assert_called_once()
    text = mock_notify.notify_react_feedback.call_args[0][3]
    assert "Action(s) taken:" in text
    assert "Scheduled prompt" in text


def test_post_loop_schedule_only_no_no_submit_msg():
    loop_out = ReactLoopResult(
        "",
        [ToolCallRecord("schedule_prompt", '{"status":"scheduled","job_id":"j1","message":"done"}')],
        [],
    )
    mock_notify = MagicMock()
    with patch.object(rr, "copilot_user_notify", mock_notify):
        rr._post_loop_ephemeral("C1", "T1", "U1", loop_out)
    text = mock_notify.notify_react_feedback.call_args[0][3]
    assert "Action(s) taken:" in text
    assert rr._NO_SUBMIT_MSG not in text


def test_post_loop_truly_empty_failed_to_process():
    loop_out = ReactLoopResult("", [], [])
    mock_notify = MagicMock()
    with patch.object(rr, "copilot_user_notify", mock_notify):
        rr._post_loop_ephemeral("C1", "T1", "U1", loop_out)
    assert "Failed to process request" in mock_notify.notify_react_feedback.call_args[0][3]


def test_post_loop_tools_but_no_notify_shows_no_submit_hint():
    loop_out = ReactLoopResult(
        "",
        [ToolCallRecord("send_thread_reply_on_behalf_of_requester", '{"error":"bad args"}')],
        [],
    )
    mock_notify = MagicMock()
    with patch.object(rr, "copilot_user_notify", mock_notify):
        rr._post_loop_ephemeral("C1", "T1", "U1", loop_out)
    assert rr._NO_SUBMIT_MSG in mock_notify.notify_react_feedback.call_args[0][3]
