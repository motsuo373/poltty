"""Configuration persistence for poltty."""

import json
import random
from datetime import datetime
from pathlib import Path
from typing import Optional

CONFIG_DIR = Path.home() / ".poltty"
CONFIG_FILE = CONFIG_DIR / "config.json"

_DEFAULT: dict = {
    "last_layout": None,
    "presets": {},
    "states": {},
}

_RANDOM_WORDS = [
    "phantom", "ghost", "shadow", "ember", "frost", "nova", "echo", "quasar",
    "vortex", "drift", "flux", "prism", "zenith", "cipher", "raven", "cobalt",
    "sparrow", "nebula", "pixel", "vector", "haze", "blade", "storm", "dusk",
    "aurora", "binary", "comet", "delta", "forge", "glitch", "helix", "iris",
    "jade", "karma", "lunar", "mosaic", "neon", "orbit", "pulse", "quartz",
    "ripple", "solstice", "tundra", "umbra", "vapor", "wave", "xenon", "zephyr",
    "arc", "beacon", "cliff", "dawn", "epoch", "flare", "grove", "haven",
]


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


# ── State helpers ──────────────────────────────────────────────────────────

def generate_state_name() -> str:
    """Generate a unique state name in the form YYYY-MM-DD+word."""
    date_str = datetime.now().strftime("%Y-%m-%d")
    existing = {s["name"] for s in list_states()}
    for _ in range(20):
        word = random.choice(_RANDOM_WORDS)
        name = f"{date_str}+{word}"
        if name not in existing:
            return name
    # Fallback: append timestamp suffix to guarantee uniqueness
    return f"{date_str}+{datetime.now().strftime('%H%M%S')}"


def save_state(
    name: str,
    columns: list[int],
    commands: Optional[list[list[str]]] = None,
) -> None:
    """Save a named layout state."""
    cfg = load()
    cfg.setdefault("states", {})[name] = {
        "columns": columns,
        "commands": commands or [],
        "created_at": datetime.now().isoformat(),
    }
    save(cfg)


def get_state(name: str) -> Optional[dict]:
    """Return a saved state by name, or None."""
    return load().get("states", {}).get(name)


def list_states() -> list[dict]:
    """Return all states sorted newest-first."""
    states = load().get("states", {})
    result = [
        {
            "name": k,
            "columns": v.get("columns", []),
            "commands": v.get("commands", []),
            "created_at": v.get("created_at", ""),
        }
        for k, v in states.items()
    ]
    result.sort(key=lambda x: x["created_at"], reverse=True)
    return result


def delete_state(name: str) -> bool:
    """Delete a state by name. Returns True on success."""
    cfg = load()
    if name in cfg.get("states", {}):
        del cfg["states"][name]
        save(cfg)
        return True
    return False
