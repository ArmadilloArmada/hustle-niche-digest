from __future__ import annotations

import re

from niche_digest.fetch import FeedItem


def _normalize_key(item: FeedItem) -> str:
    if item.link:
        return item.link.rstrip("/").lower()
    title = re.sub(r"\W+", " ", item.title.lower()).strip()
    return f"{item.source.lower()}::{title}"


def dedupe(items: list[FeedItem]) -> list[FeedItem]:
    seen: set[str] = set()
    unique: list[FeedItem] = []
    for item in items:
        key = _normalize_key(item)
        if key in seen:
            continue
        seen.add(key)
        unique.append(item)
    return unique


def rank(items: list[FeedItem], limit: int) -> list[FeedItem]:
    ordered = sorted(
        items,
        key=lambda it: (
            it.novelty_score,
            it.published.timestamp() if it.published else 0.0,
        ),
        reverse=True,
    )
    return ordered[: max(1, limit)]
