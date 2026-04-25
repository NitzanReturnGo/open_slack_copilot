import common.tools.send_thread_reply_on_behalf_of_requester  # noqa: F401
from common.tools.copilot_tool import get_copilot_tool
from common.tools.send_thread_reply_as_app import (
    SEND_THREAD_REPLY_AS_APP,
    SEND_THREAD_REPLY_AS_APP_TOOL,
)


def test_app_tool_built_not_registered():
    assert SEND_THREAD_REPLY_AS_APP_TOOL["function"]["name"] == "send_thread_reply_as_app"
    assert get_copilot_tool("send_thread_reply_as_app") is None
    assert SEND_THREAD_REPLY_AS_APP.name == "send_thread_reply_as_app"
    assert SEND_THREAD_REPLY_AS_APP.execute_after_confirm is not None
