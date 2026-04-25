"""Slack API–specific errors."""


class OAuthNotConnectedError(Exception):
    """Raised when the requester has no user OAuth token (cannot post on their behalf)."""

    def __init__(self, user_id: str) -> None:
        self.user_id = (user_id or "").strip()
        if self.user_id:
            super().__init__(
                "No OAuth is connected for this user. "
                f"Connect Slack user OAuth so <@{self.user_id}> can send thread replies and DMs in their name."
            )
        else:
            super().__init__(
                "No Slack user OAuth is connected. Connect OAuth so the requester can send thread replies and DMs in their name."
            )
