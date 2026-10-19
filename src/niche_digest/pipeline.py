from __future__ import annotations

from datetime import date
from pathlib import Path

from niche_digest.config import load_config
from niche_digest.draft import draft_digest
from niche_digest.fetch import fetch_all_feeds
from niche_digest.rank import dedupe, rank


def run(config_path: Path, out_dir: Path, issue_date: date | None = None) -> Path:
    config = load_config(config_path)
    issue = issue_date or date.today()
    items = fetch_all_feeds(config)
    unique = dedupe(items)
    top = rank(unique, int(config.get("max_items", 8)))
    markdown = draft_digest(str(config["niche_name"]), top, issue)

    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"digest-{issue.isoformat()}.md"
    out_path.write_text(markdown, encoding="utf-8")
    return out_path
