"""Config loading and discovery."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import yaml

CONFIG_FILENAME = "houseofmath.config.yaml"
EXAMPLE_FILENAME = "houseofmath.config.example.yaml"


def repo_root() -> Path:
    """Best-effort discovery of the repo root.

    Walks up from CWD looking for `pyproject.toml`. Falls back to CWD.
    """
    here = Path.cwd().resolve()
    for parent in [here, *here.parents]:
        if (parent / "pyproject.toml").exists():
            return parent
    return here


def config_path() -> Path:
    return repo_root() / CONFIG_FILENAME


def example_config_path() -> Path:
    return repo_root() / EXAMPLE_FILENAME


def question_bank_path() -> Path:
    return repo_root() / "Question Bank"


def history_db_path() -> Path:
    base = Path(os.environ.get("HOUSEOFMATH_HOME", Path.home() / ".houseofmath"))
    base.mkdir(parents=True, exist_ok=True)
    return base / "history.db"


def load_config() -> dict[str, Any]:
    """Load config from disk. Returns sensible defaults if missing."""
    p = config_path()
    if not p.exists():
        return {"provider": "none"}
    try:
        with p.open("r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
    except yaml.YAMLError as e:
        raise RuntimeError(f"Could not parse {p}: {e}") from e
    data.setdefault("provider", "none")
    return data


def save_config(cfg: dict[str, Any]) -> Path:
    p = config_path()
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open("w", encoding="utf-8") as f:
        yaml.safe_dump(cfg, f, sort_keys=False)
    return p
