# M6 — Tool: Send DM

[← Back to PRD](../../PRD.md)

## Requirements

- **Slack API for DMs** — `slack_api` supports `send_dm(user_id, text)` to send direct messages
- **Expose as LLM tool** — available as a LiteLLM function/tool the LLM can call during draft generation or skill execution
- **Confirmation required** — LLM cannot send DMs autonomously; every DM must be confirmed by the user via ephemeral before sending
- **Any content** — the LLM can compose any text for the DM (content defined by the skill/context)
- **User resolution** — works with M5's `resolve_user` to get the target user ID

## Architecture

### Modules

- `common/slack/slack_api/slack_api.py` — exposes the slack_bolt client directly, plus helper functions as needed (e.g. DM sending via the client's `conversations.open` + `chat.postMessage`, and `send_dm_on_behalf_of_requester` using a stored user OAuth token)
- `common/tools/send_dm_base_tool_helper.py` — shared builder for DM tools (LLM schema, user resolution, confirmation queueing, after-confirm post hook)
- `common/tools/send_dm_as_app.py` — registered LiteLLM tool that posts as the app/bot after requester confirmation
- `common/tools/send_dm_on_behalf_of_requester.py` — sibling tool built with the same helper; posts in the requester's name via user OAuth. **Not** registered in the default tool set (future use)
- `common/slack/slack_bot/tool_confirmation.py` — shared Block Kit confirmation flow (Revise + Confirm) used by all tools including DMs
- `common/llm/llm_client/llm_client.py` — already supports tools from M5
- `core/slack_bot.py` — wires the registered tool set (including `send_dm_as_app`) into the copilot pipeline

### Data Flow

```
LLM decides to send a DM during draft generation
       │
       ├── LLM calls send_dm_as_app(user="Nitzan", message="Hey, please review the PR")
       │
       ▼
send_dm_as_app tool (does NOT send yet)
       │
       ├── resolve_user("Nitzan") → <@U123>
       ├── queue_tool_confirmation(...) → pending DM payload
       │
       ▼
tool_confirmation.py (shared Block Kit ephemeral)
       │
       ├── ephemeral to requesting user with Revise + Confirm ("Send DM")
       │
       ├── user clicks [Send DM]
       │     └── slack_api.send_dm("U123", "Hey, please review the PR")
       │
       └── user clicks [Revise]
             └── modal → re-run ReAct with the same context_kind
```

### LiteLLM Tool Definition

```
Tool name: send_dm_as_app
Description: "Queue a direct message to a workspace member. The requester confirms in Slack; the DM is sent as the app (bot), not as the user."
Parameters:
  - user (string): display name or user ID of the recipient
  - message (string): the DM content
Returns: JSON with `status: tool_confirmation_requested` (actual sending happens after user confirms)
```

### Key Decisions

- **Never auto-send** — all DMs require explicit user confirmation via Slack interactive buttons
- **Ephemeral confirmation** — the DM preview is shown as ephemeral (only visible to the requesting user)
- **Shared confirmation UI** — Revise + Confirm Block Kit flow is reused across DMs and thread replies
- **Tool returns immediately** — the LLM gets JSON including `status: tool_confirmation_requested` and can continue generating the rest of the draft
- **Two identity variants** — `send_dm_as_app` (registered today) sends from the bot; `send_dm_on_behalf_of_requester` (prepared, unregistered) will send from the requester once user OAuth is wired through the full flow

## STP — Software Test Procedure

### STP-6.1: Happy path — LLM sends DM, user confirms

- **Precondition**: User "Dan" (U456) exists. Skill instructs LLM to send a follow-up DM.
- **Input**: LLM calls `send_dm_as_app(user="Dan", message="Please check the thread")`
- **Expected**: Ephemeral to requesting user: "Draft DM to @Dan: 'Please check the thread' [Send DM] [Revise]". User clicks Send DM. DM sent to Dan.

### STP-6.2: User revises the DM

- **Precondition**: Same as STP-6.1.
- **Input**: User clicks Revise, submits revision instruction.
- **Expected**: ReAct re-runs with the same context; a new confirmation ephemeral is shown with the revised draft.

### STP-6.3: Multiple DMs in one draft

- **Precondition**: Skill requires DMs to 3 people.
- **Input**: LLM calls `send_dm_as_app` 3 times.
- **Expected**: 3 separate confirmation ephemerals. User can confirm/revise each independently.

### STP-6.4: Recipient not found

- **Precondition**: LLM tries to DM "NonExistent".
- **Input**: `send_dm_as_app(user="NonExistent", message="...")`
- **Expected**: Tool returns error. LLM handles gracefully — reports inability to find user.

### STP-6.5: LLM doesn't use DM tool

- **Precondition**: Simple reply draft, no DM needed.
- **Input**: `/copilot`
- **Expected**: Tool not invoked. Draft generated normally.

### STP-6.6: DM with long content

- **Precondition**: LLM composes a 500-word DM.
- **Input**: `send_dm_as_app(user="Dan", message="<long text>")`
- **Expected**: Full content shown in confirmation ephemeral. On confirm, full content sent as DM.

### STP-6.7: Slack API failure on DM send

- **Precondition**: User confirms, but Slack API returns error.
- **Input**: User clicks Send DM.
- **Expected**: Ephemeral error: "Failed to send: ...". Fail fast.

## Unit Tests

**Files**: `common/tools/send_dm_as_app_unit_test.py`, `common/tools/send_dm_on_behalf_of_requester_unit_test.py`, `common/slack/slack_bot/tool_confirmation_unit_test.py`

**Mock**: Slack API

### Test Cases

- **test_tool_returns_pending** — call `send_dm_as_app` tool, assert JSON has `tool_confirmation_requested`, NOT sent
- **test_resolve_user_called** — assert `resolve_user` invoked with the user parameter
- **test_confirmation_ephemeral_sent** — assert ephemeral with Block Kit buttons sent to requesting user
- **test_confirm_sends_dm** — simulate confirm action, assert `slack_api.send_dm` called with correct user_id and text
- **test_on_behalf_variant_posts_with_user_token** — assert `slack_api.send_dm_on_behalf_of_requester(requester, target, text)` called for the unregistered sibling tool
- **test_oauth_not_connected_surfaces_error** — on-behalf variant: `OAuthNotConnectedError` message is returned to the user
- **test_dm_failure_error_ephemeral** — mock `send_dm` raising error, assert error ephemeral sent
- **test_user_not_found** — mock `resolve_user` returning None, assert tool returns error
- **test_tool_definition_schema** — assert schema matches LiteLLM format
