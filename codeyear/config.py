"""Optional user-level defaults for the CLI.

Reads ``~/.codeyear.json`` (or ``$CODEYEAR_CONFIG``). Invalid keys/types are
ignored so a broken config never prevents a scan. Explicit CLI flags win.
"""

from __future__ import annotations

import json
import os
from pathlib import Path

ENV_PATH = "CODEYEAR_CONFIG"

# key -> expected type
SCHEMA = {
    "roots": list,
    "year": int,
    "out": str,
    "author": str,
    "all_authors": bool,
    "aliases": list,
    "compare": bool,
    "fallback_previous": bool,
    "all_branches": bool,
    "no_mailmap": bool,
    "jobs": int,
    "max_depth": int,
    "timeout": int,
    "theme": str,
    "max_commits": int,
    "open": bool,
    "tz": str,
    "exclude": list,
    "rolling": bool,
    "github_user": str,
    "profile_repo": str,
    "push_profile": bool,
}


def path() -> Path:
    override = os.environ.get(ENV_PATH)
    if override:
        return Path(override).expanduser()
    return Path.home() / ".codeyear.json"


def load() -> dict:
    file = path()
    if not file.exists():
        return {}
    try:
        raw = json.loads(file.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    if not isinstance(raw, dict):
        return {}

    clean: dict = {}
    for key, expected in SCHEMA.items():
        if key not in raw:
            continue
        value = raw[key]
        if expected is list:
            if isinstance(value, list) and all(isinstance(item, str) for item in value):
                clean[key] = value
        elif expected is bool:
            if isinstance(value, bool):
                clean[key] = value
        elif expected is int:
            if isinstance(value, int) and not isinstance(value, bool):
                clean[key] = value
        elif expected is str and isinstance(value, str):
            if key == "theme" and value not in {
                "paper", "mono", "forest", "ocean",
            }:
                continue
            clean[key] = value
    if clean.get("max_commits", 1) <= 0:
        clean.pop("max_commits", None)
    if clean.get("jobs", 1) <= 0:
        clean.pop("jobs", None)
    return clean


def save(values: dict) -> Path:
    """Validate and persist user defaults to ``~/.codeyear.json``."""
    merged = load()
    merged.update(values)
    clean: dict = {}
    for key, expected in SCHEMA.items():
        if key not in merged:
            continue
        value = merged[key]
        if expected is list:
            if isinstance(value, list) and all(isinstance(item, str) for item in value):
                clean[key] = value
        elif expected is bool:
            if isinstance(value, bool):
                clean[key] = value
        elif expected is int:
            if isinstance(value, int) and not isinstance(value, bool):
                clean[key] = value
        elif expected is str and isinstance(value, str):
            if key == "theme" and value not in {"paper", "mono", "forest", "ocean"}:
                continue
            clean[key] = value
    target = path()
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(
        json.dumps(clean, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return target
