"""Configuration persistence for polltty."""

import json
from pathlib import Path
from typing import Optional

CONFIG_DIR = Path.home() / ".polltty"
CONFIG_FILE = CONFIG_DIR / "config.json"

_DEFAULT: dict = {
    "last_layout": None,
    "presets": {},
}


def _ensure_dir() -> None:
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)


def load() -> dict:
    """Load configuration from disk, returning defaults if absent."""
    _ensure_dir()
    if CONFIG_FILE.exists():
        try:
            with CONFIG_FILE.open() as fh:
                return json.load(fh)
        except (json.JSONDecodeError, OSError):
            pass
    return _DEFAULT.copy()


def save(cfg: dict) -> None:
    """Persist configuration to disk."""
    _ensure_dir()
    with CONFIG_FILE.open("w") as fh:
        json.dump(cfg, fh, indent=2)


# ── Last-layout helpers ────────────────────────────────────────────────────

def save_last_layout(
    columns: list[int],
    commands: Optional[list[list[str]]] = None,
) -> None:
    cfg = load()
    cfg["last_layout"] = {
        "columns": columns,
        "commands": commands or [],
    }
    save(cfg)


def get_last_layout() -> Optional[dict]:
    return load().get("last_layout")


# ── Preset helpers ─────────────────────────────────────────────────────────

def save_preset(
    name: str,
    columns: list[int],
    commands: Optional[list[list[str]]] = None,
) -> None:
    cfg = load()
    cfg.setdefault("presets", {})[name] = {
        "columns": columns,
        "commands": commands or [],
    }
    save(cfg)


def get_preset(name: str) -> Optional[dict]:
    return load().get("presets", {}).get(name)


def list_presets() -> list[str]:
    return list(load().get("presets", {}).keys())


def delete_preset(name: str) -> bool:
    cfg = load()
    if name in cfg.get("presets", {}):
        del cfg["presets"][name]
        save(cfg)
        return True
    return False
