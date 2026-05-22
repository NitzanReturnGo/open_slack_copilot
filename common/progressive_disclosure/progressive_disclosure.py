import json
import re
from pathlib import Path

from common.log import log
from common.llm.llm_client import llm_client

SKILLS_ROOT = Path.home() / ".open_slack_copilot" / "skills"
_SKILL_KINDS = ("reply", "watcher")
# Reply skill folder name: one path segment, letters, underscore, hyphen.
_REPLY_SKILL_FOLDER_NAME_RE = re.compile(r"^[a-zA-Z_-]+\Z")
_BUNDLED_DEFAULT_INSTRUCTION = (Path(__file__).parent / "default_reply_instruction.md").read_text().strip()
USER_DEFAULT_INSTRUCTION_PATH = Path.home() / ".open_slack_copilot" / "skills" / "reply" / "default.md"

SELECTION_PROMPT = (
    "You are selecting relevant skills for drafting a Slack reply.\n"
    "Given the thread context and available skills, return a JSON array of "
    "skill references that are relevant. Return [] if none match.\n"
    "Each reference must be exactly as listed (kind/name).\n\n"
    "Available skills:\n{skill_list}\n\n"
    "Thread context:\n{thread_context}\n\n"
    "Return ONLY a JSON array, e.g. [\"reply/polite_reply\", \"watcher/checklist\"]"
)


@log
def select_skills(skill_type: str, thread_messages: list[dict], user_text: str) -> list[str]:
    entries = _skill_entries_for_kind(skill_type)
    if not entries:
        return []

    thread_context = _summarize_context(thread_messages, user_text)
    skill_list = "\n".join(f"- {ref}" for ref, _ in entries)
    prompt = SELECTION_PROMPT.format(skill_list=skill_list, thread_context=thread_context)

    response = llm_client.generate(prompt)
    valid_refs = [ref for ref, _ in entries]
    selected_refs = _parse_selection(response, valid_refs)
    return [text for ref, text in entries if ref in selected_refs]


def is_safe_reply_skill_folder_name(name: str) -> bool:
    """True when ``name`` is a single safe folder segment (``skills/reply/<name>/``)."""
    n = (name or "").strip()
    return bool(n) and _REPLY_SKILL_FOLDER_NAME_RE.match(n) is not None


def load_forced_reply_skill(skill_folder: str) -> tuple[str, str] | None:
    """Load ``reply/<skill_folder>/SKILL.md`` when present."""
    cid = (skill_folder or "").strip()
    if not is_safe_reply_skill_folder_name(cid):
        return None
    d = SKILLS_ROOT / "reply" / cid
    if not d.is_dir() or not (d / "SKILL.md").is_file():
        return None
    ref = f"reply/{cid}"
    skill_text = (d / "SKILL.md").read_text().strip()
    return ref, skill_text


def reply_skill_display_name(skill_folder: str, skill_text: str | None = None) -> str:
    """Human title from SKILL.md ``# Heading`` or the folder name."""
    text = skill_text
    if text is None:
        loaded = load_forced_reply_skill(skill_folder)
        if loaded is None:
            return (skill_folder or "").strip() or "unknown"
        _, text = loaded
    for line in (text or "").splitlines():
        stripped = line.strip()
        if stripped.startswith("#"):
            return stripped.lstrip("#").strip()
    return (skill_folder or "").strip() or "unknown"


def get_default_instruction() -> str:
    if USER_DEFAULT_INSTRUCTION_PATH.is_file():
        return USER_DEFAULT_INSTRUCTION_PATH.read_text().strip()
    return _BUNDLED_DEFAULT_INSTRUCTION


def _skill_entries_for_kind(kind: str) -> list[tuple[str, str]]:
    if kind not in _SKILL_KINDS:
        return []
    base = SKILLS_ROOT / kind
    if not base.is_dir():
        return []
    out: list[tuple[str, str]] = []
    for d in base.iterdir():
        if d.is_dir() and (d / "SKILL.md").is_file():
            out.append((f"{kind}/{d.name}", (d / "SKILL.md").read_text().strip()))
    return out


def _parse_selection(response: str, valid_titles: list[str]) -> list[str]:
    try:
        start = response.index("[")
        end = response.index("]") + 1
        selected = json.loads(response[start:end])
        return [s for s in selected if s in valid_titles]
    except (ValueError, json.JSONDecodeError):
        return []


def _summarize_context(thread_messages: list[dict], user_text: str) -> str:
    # TODO: instead of thread_messages[-5:] need to take first 10 and then last 10 and put in the middle something like "20 other messages..."
    lines = [f"<@{m.get('user', '?')}>: {m.get('text', '')}" for m in thread_messages[-5:]]
    if user_text:
        lines.append(f"User instruction: {user_text}")
    return "\n".join(lines)
