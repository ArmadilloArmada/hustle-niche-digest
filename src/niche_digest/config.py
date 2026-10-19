from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml


def load_config(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise FileNotFoundError(
            f"Config not found: {path}\n"
            "Copy the example first:  cp config.example.yaml config.yaml"
        )
    with path.open(encoding="utf-8") as fh:
        data = yaml.safe_load(fh) or {}
    if not isinstance(data, dict):
        raise ValueError("config.yaml must be a mapping")
    feeds = data.get("feeds") or []
    if not feeds:
        raise ValueError("config.yaml must list at least one feed under `feeds`")
    data.setdefault("niche_name", "Niche Digest")
    data.setdefault("max_items", 8)
    data.setdefault(
        "user_agent",
        "hustle-niche-digest/0.1 (+public-RSS-only)",
    )
    return data
