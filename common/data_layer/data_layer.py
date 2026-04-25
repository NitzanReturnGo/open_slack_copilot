"""Factory for KeyValueCollection backends."""

from __future__ import annotations

from pathlib import Path

from common.data_layer.file_key_value_collection import FileKeyValueCollection
from common.data_layer.key_value_collection import KeyValueCollection
from config.config import settings

_DEFAULT_ROOT = Path.home() / ".open_slack_copilot"


def _data_root() -> Path:
    raw = settings.get("data_layer", {}).get("root", str(_DEFAULT_ROOT))
    return Path(str(raw)).expanduser().resolve()


def get_collection(name: str) -> KeyValueCollection:
    """
    Return a collection under the configured data root, e.g.
    ``~/.open_slack_copilot/<name>/`` for the file backend.
    """
    cfg = settings.get("data_layer", {}) or {}
    backend = (cfg.get("backend") or "file").strip().lower()
    if backend != "file":
        raise NotImplementedError(
            f"data_layer backend {backend!r} is not implemented (only 'file' is supported).",
        )
    safe = (name or "").strip()
    if not safe or ".." in safe or "/" in safe or "\\" in safe:
        raise ValueError("Invalid collection name")
    root = _data_root() / safe
    return FileKeyValueCollection(root)
