from __future__ import annotations

from pathlib import Path
import json
import os
from typing import Any

from .templates import DEFAULT_CONFIG
from .utils import ContextError, write_utf8


def config_path() -> Path:
    override = os.environ.get("AGENT_CONTEXT_CONFIG_DIR")
    if override:
        return Path(override).expanduser().resolve() / "config.json"
    return Path.home() / ".agent-context" / "config.json"


def load_config(create: bool = False) -> dict[str, Any]:
    path = config_path()
    if not path.exists():
        config = dict(DEFAULT_CONFIG)
        if create:
            save_config(config)
        return config
    try:
        loaded = json.loads(path.read_text(encoding="utf-8"))
    except UnicodeDecodeError as exc:
        raise ContextError(
            "Unable to read config.",
            "File encoding is invalid.",
            f"Fix or remove:\n\n{path}",
        ) from exc
    except json.JSONDecodeError as exc:
        raise ContextError(
            "Unable to read config.",
            str(exc),
            f"Fix or remove:\n\n{path}",
        ) from exc
    config = dict(DEFAULT_CONFIG)
    config.update(loaded)
    return config


def save_config(config: dict[str, Any]) -> None:
    text = json.dumps(config, ensure_ascii=False, indent=2)
    write_utf8(config_path(), text)
