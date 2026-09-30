"""Remember the user's Anthropic API key between runs of the desktop app.

The key is stored in a small JSON file in the user's own profile
(%APPDATA%\\DocumentSummarizer on Windows, ~/.config/document-summarizer
elsewhere). It is never bundled into the program.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path


def config_path() -> Path:
    if sys.platform == "win32" and os.environ.get("APPDATA"):
        base = Path(os.environ["APPDATA"]) / "DocumentSummarizer"
    else:
        base = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config")) / "document-summarizer"
    return base / "config.json"


def _read() -> dict:
    try:
        return json.loads(config_path().read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def load_api_key() -> str | None:
    """Environment variable first, then the saved key."""
    return os.environ.get("ANTHROPIC_API_KEY") or _read().get("api_key") or None


def save_api_key(key: str) -> None:
    path = config_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    data = _read()
    data["api_key"] = key.strip()
    path.write_text(json.dumps(data), encoding="utf-8")
    if sys.platform != "win32":
        path.chmod(0o600)


def forget_api_key() -> None:
    data = _read()
    if data.pop("api_key", None) is not None:
        config_path().write_text(json.dumps(data), encoding="utf-8")
