from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from typing import Any
from xml.etree import ElementTree as ET

import feedparser
import httpx


@dataclass(frozen=True)
class FeedItem:
    id: str
    source: str
    title: str
    link: str
    summary: str
    published: datetime | None

    @property
    def novelty_score(self) -> float:
        """Rough novelty/impact heuristic for ranking without an LLM."""
        score = 0.0
        title_l = self.title.lower()
        summary_l = self.summary.lower()
        text = f"{title_l} {summary_l}"

        if re.search(r"\b(major|breaking|security|cve|critical)\b", text):
            score += 3.0
        if re.search(r"\b(ga|stable|lts|release)\b", text):
            score += 1.5
        if re.search(r"\bv?\d+\.\d+(\.\d+)?\b", title_l):
            score += 1.0
        if re.search(r"\b(alpha|beta|rc|preview|nightly)\b", text):
            score -= 0.5
        if self.published is not None:
            age_hours = (
                datetime.now(timezone.utc) - self.published.astimezone(timezone.utc)
            ).total_seconds() / 3600
            # Prefer fresher items.
            score += max(0.0, 2.0 - age_hours / 72.0)
        return score


def _parse_date(value: Any) -> datetime | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=timezone.utc)
    if isinstance(value, (tuple, list)) and len(value) >= 6:
        try:
            return datetime(*value[:6], tzinfo=timezone.utc)
        except (TypeError, ValueError):
            return None
    if isinstance(value, str) and value.strip():
        try:
            return parsedate_to_datetime(value)
        except (TypeError, ValueError, IndexError):
            pass
        try:
            return datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            return None
    return None


def _strip_html(text: str) -> str:
    cleaned = re.sub(r"<[^>]+>", " ", text or "")
    return re.sub(r"\s+", " ", cleaned).strip()


def _stable_id(source: str, title: str, link: str) -> str:
    raw = f"{source}|{link}|{title}".encode("utf-8")
    return hashlib.sha256(raw).hexdigest()[:16]


def _entries_from_xml(xml_text: str) -> list[dict[str, Any]]:
    """Minimal Atom/RSS fallback when feedparser returns nothing usable."""
    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError:
        return []

    ns = {
        "atom": "http://www.w3.org/2005/Atom",
        "content": "http://purl.org/rss/1.0/modules/content/",
    }
    entries: list[dict[str, Any]] = []

    for entry in root.findall("atom:entry", ns) or root.findall(
        "{http://www.w3.org/2005/Atom}entry"
    ):
        title_el = entry.find("atom:title", ns)
        link_el = entry.find("atom:link[@rel='alternate']", ns)
        if link_el is None:
            link_el = entry.find("atom:link", ns)
        summary_el = entry.find("atom:summary", ns)
        if summary_el is None:
            summary_el = entry.find("atom:content", ns)
        updated_el = entry.find("atom:updated", ns)
        if updated_el is None:
            updated_el = entry.find("atom:published", ns)
        id_el = entry.find("atom:id", ns)
        entries.append(
            {
                "id": (id_el.text if id_el is not None else "") or "",
                "title": (title_el.text if title_el is not None else "") or "",
                "link": (link_el.get("href") if link_el is not None else "") or "",
                "summary": (summary_el.text if summary_el is not None else "") or "",
                "published": updated_el.text if updated_el is not None else None,
            }
        )

    channel = root.find("channel")
    if channel is not None:
        for item in channel.findall("item"):
            title_el = item.find("title")
            link_el = item.find("link")
            desc_el = item.find("description")
            guid_el = item.find("guid")
            pub_el = item.find("pubDate")
            entries.append(
                {
                    "id": (guid_el.text if guid_el is not None else "") or "",
                    "title": (title_el.text if title_el is not None else "") or "",
                    "link": (link_el.text if link_el is not None else "") or "",
                    "summary": (desc_el.text if desc_el is not None else "") or "",
                    "published": pub_el.text if pub_el is not None else None,
                }
            )
    return entries


def fetch_feed(
    name: str,
    url: str,
    *,
    user_agent: str,
    timeout: float = 30.0,
) -> list[FeedItem]:
    headers = {"User-Agent": user_agent, "Accept": "application/atom+xml, application/rss+xml, application/xml, text/xml, */*"}
    with httpx.Client(timeout=timeout, follow_redirects=True, headers=headers) as client:
        response = client.get(url)
        response.raise_for_status()
        body = response.text

    parsed = feedparser.parse(body)
    raw_entries: list[dict[str, Any]] = []
    for entry in parsed.entries:
        raw_entries.append(
            {
                "id": getattr(entry, "id", "") or getattr(entry, "guid", "") or "",
                "title": getattr(entry, "title", "") or "",
                "link": getattr(entry, "link", "") or "",
                "summary": getattr(entry, "summary", "")
                or getattr(entry, "description", "")
                or "",
                "published": getattr(entry, "published_parsed", None)
                or getattr(entry, "updated_parsed", None)
                or getattr(entry, "published", None)
                or getattr(entry, "updated", None),
            }
        )
    if not raw_entries:
        raw_entries = _entries_from_xml(body)

    items: list[FeedItem] = []
    for entry in raw_entries:
        title = _strip_html(str(entry.get("title") or "")).strip() or "(untitled)"
        link = str(entry.get("link") or "").strip()
        summary = _strip_html(str(entry.get("summary") or ""))[:500]
        published = _parse_date(entry.get("published"))
        eid = str(entry.get("id") or "").strip() or _stable_id(name, title, link)
        items.append(
            FeedItem(
                id=eid,
                source=name,
                title=title,
                link=link,
                summary=summary,
                published=published,
            )
        )
    return items


def fetch_all_feeds(config: dict[str, Any]) -> list[FeedItem]:
    user_agent = config["user_agent"]
    all_items: list[FeedItem] = []
    errors: list[str] = []
    for feed in config["feeds"]:
        name = str(feed.get("name") or feed.get("url") or "feed")
        url = str(feed["url"])
        try:
            all_items.extend(fetch_feed(name, url, user_agent=user_agent))
        except Exception as exc:  # noqa: BLE001 — keep pipeline resilient
            errors.append(f"{name}: {exc}")
    if errors:
        print(f"Warning: {len(errors)} feed(s) failed:")
        for err in errors:
            print(f"  - {err}")
    if not all_items and errors:
        raise RuntimeError("All feeds failed; cannot draft digest.")
    return all_items
