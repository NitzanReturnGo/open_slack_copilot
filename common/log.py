import functools
import json
import logging
import os
import sys
from typing import Any

from config.config import settings

LOGGER_NAME = "open_slack_copilot"
TEST_LOGGER_PREFIX = f"{LOGGER_NAME}.test"

_LEVELS: dict[str, int] = {
    "CRITICAL": logging.CRITICAL,
    "ERROR": logging.ERROR,
    "WARNING": logging.WARNING,
    "INFO": logging.INFO,
    "DEBUG": logging.DEBUG,
}

_logger = logging.getLogger(LOGGER_NAME)

_LOG_SANITIZE_CONFIG = settings.log_sanitize
_DEFAULT_MAX_STR = _LOG_SANITIZE_CONFIG.get("max_str", 500)
_DEFAULT_MAX_LIST = _LOG_SANITIZE_CONFIG.get("max_list", 8)
_DEFAULT_MAX_DEPTH = _LOG_SANITIZE_CONFIG.get("max_depth", 12)

_REDACT_KEYS = frozenset(
    {
        "token",
        "response_url",
        "trigger_id",
        "client_secret",
        "access_token",
        "refresh_token",
        "password",
        "app_password",
    }
)


def _is_pytest_running() -> bool:
    return "pytest" in sys.modules or bool(os.environ.get("PYTEST_CURRENT_TEST"))


def resolve_log_level(level: str | int) -> int:
    if isinstance(level, int):
        return level
    key = str(level).strip().upper()
    if key not in _LEVELS:
        raise ValueError(f"Unknown log level: {level!r}; expected one of {sorted(_LEVELS)}")
    return _LEVELS[key]


def _configured_level(*, test_mode: bool) -> int:
    cfg = settings.get("logging", {})
    key = "test_level" if test_mode else "level"
    default = "INFO" if test_mode else "DEBUG"
    return resolve_log_level(cfg.get(key, default))


def configure_app_logging(*, test_mode: bool | None = None) -> None:
    """Apply ``logging.level`` (app) or ``logging.test_level`` (pytest) from config."""
    if test_mode is None:
        test_mode = _is_pytest_running()
    level = _configured_level(test_mode=test_mode)
    _logger.setLevel(level)
    if not _logger.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(logging.Formatter("%(message)s"))
        _logger.addHandler(handler)
    for handler in _logger.handlers:
        handler.setLevel(level)


def get_test_logger(name: str) -> logging.Logger:
    """Logger for test step output (INFO); respects ``logging.test_level`` under pytest."""
    return logging.getLogger(f"{TEST_LOGGER_PREFIX}.{name}")


def _to_json(obj: Any) -> str:
    return json.dumps(obj, default=str)


def _sanitize(
    obj: Any,
    *,
    depth: int = 0,
    max_depth: int = _DEFAULT_MAX_DEPTH,
    max_str: int = _DEFAULT_MAX_STR,
    max_list: int = _DEFAULT_MAX_LIST,
) -> Any:
    """Copy-safe shrink + redact for log output (Slack payloads, LLM prompts, etc.)."""
    if depth > max_depth:
        return "<max depth>"
    if obj is None or isinstance(obj, bool):
        return obj
    if isinstance(obj, (int, float)):
        return obj
    if isinstance(obj, str):
        if len(obj) > max_str:
            return f"{obj[:max_str]}... [truncated, {len(obj)} chars total]"
        return obj
    if isinstance(obj, dict):
        out: dict[Any, Any] = {}
        for k, v in obj.items():
            ks = k.lower() if isinstance(k, str) else ""
            if isinstance(k, str) and (
                ks in _REDACT_KEYS or ks.endswith("_token") or "secret" in ks
            ):
                out[k] = "<redacted>"
            elif isinstance(k, str) and ks == "blocks":
                bl = v if isinstance(v, list) else []
                out[k] = f"<{len(bl)} blocks>"
            else:
                out[k] = _sanitize(
                    v, depth=depth + 1, max_depth=max_depth, max_str=max_str, max_list=max_list
                )
        return out
    if isinstance(obj, (list, tuple)):
        n = len(obj)
        if n > max_list:
            head = [
                _sanitize(x, depth=depth + 1, max_depth=max_depth, max_str=max_str, max_list=max_list)
                for x in obj[:max_list]
            ]
            return [*head, f"... and {n - max_list} more items"]
        return [
            _sanitize(x, depth=depth + 1, max_depth=max_depth, max_str=max_str, max_list=max_list)
            for x in obj
        ]
    return str(obj)


def log(fn):
    @functools.wraps(fn)
    def wrapper(*args, **kwargs):
        name = fn.__name__
        safe = {
            "args": _sanitize(list(args)),
            "kwargs": _sanitize(dict(kwargs)),
        }
        _logger.debug("%s started %s", name, _to_json(safe))
        try:
            result = fn(*args, **kwargs)
            _logger.debug("%s returned %s", name, _to_json(_sanitize(result)))
            return result
        except Exception as e:
            _logger.error("%s raised %s: %s", name, type(e).__name__, e)
            raise

    return wrapper


configure_app_logging()
