"""Slack API–specific errors."""


class OAuthNotConnectedError(Exception):
    """Raised when the requester has no user OAuth token (cannot post on their behalf)."""

    def __init__(self, user_id: str) -> None:
        self.user_id = (user_id or "").strip()
        if self.user_id:
            super().__init__(
                "No OAuth is connected for this user. "
                f"Connect Slack user OAuth to post in the thread on behalf of <@{self.user_id}>."
            )
        else:
            super().__init__(
                "No Slack user OAuth is connected. Connect OAuth to post on behalf of the requester."
            )
