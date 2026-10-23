"""Loaders for the contracts in specs/ (presets, disclosure lines, ...)."""

import json
from functools import lru_cache
from pathlib import Path
from typing import Any

SPECS_DIR = Path(__file__).resolve().parents[3] / "specs"


@lru_cache
def load_json(relative: str) -> Any:
    return json.loads((SPECS_DIR / relative).read_text(encoding="utf-8"))
