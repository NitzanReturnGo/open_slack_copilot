"""Run localhost HTTP server for Slack user OAuth (stores token via oauth_token_store)."""

from common.slack.slack_user_oauth.local_server import run_user_oauth_server


def main() -> None:
    run_user_oauth_server()


if __name__ == "__main__":
    main()
