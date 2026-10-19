from __future__ import annotations

import html
import os
import re
from pathlib import Path
from urllib.parse import quote

import httpx

from niche_digest.approve import is_approved, resolve_digest

BUTTONDOWN_API = "https://api.buttondown.com/v1/emails"


def email_gate_ok(i_approved: bool = False) -> bool:
    """Explicit second gate for anything that touches an ESP / 'send' surface."""
    if i_approved:
        return True
    return os.environ.get("APPROVED", "").strip() == "1"


def export_dir(out_dir: Path) -> Path:
    return out_dir / "export"


def _extract_subject(markdown: str, fallback: str) -> str:
    for line in markdown.splitlines():
        stripped = line.strip()
        if stripped.startswith("# "):
            return stripped[2:].strip() or fallback
    return fallback


def _markdown_to_html(markdown: str) -> str:
    """Minimal Markdown → HTML for paste into Substack/Buttondown editors."""
    lines = markdown.splitlines()
    parts: list[str] = [
        "<!DOCTYPE html>",
        '<html lang="en"><head><meta charset="utf-8">',
        "<title>Digest email draft</title>",
        "</head><body>",
    ]
    in_list = False
    paragraph: list[str] = []

    def flush_paragraph() -> None:
        nonlocal paragraph
        if paragraph:
            text = " ".join(paragraph)
            parts.append(f"<p>{_inline(text)}</p>")
            paragraph = []

    def close_list() -> None:
        nonlocal in_list
        if in_list:
            parts.append("</ul>")
            in_list = False

    for raw in lines:
        line = raw.rstrip()
        if not line.strip():
            flush_paragraph()
            close_list()
            continue
        if line.startswith("# "):
            flush_paragraph()
            close_list()
            parts.append(f"<h1>{_inline(line[2:].strip())}</h1>")
        elif line.startswith("## "):
            flush_paragraph()
            close_list()
            parts.append(f"<h2>{_inline(line[3:].strip())}</h2>")
        elif line.startswith("### "):
            flush_paragraph()
            close_list()
            parts.append(f"<h3>{_inline(line[4:].strip())}</h3>")
        elif re.match(r"^[-*] ", line.strip()):
            flush_paragraph()
            if not in_list:
                parts.append("<ul>")
                in_list = True
            parts.append(f"<li>{_inline(line.strip()[2:])}</li>")
        elif line.strip() == "---":
            flush_paragraph()
            close_list()
            parts.append("<hr>")
        else:
            close_list()
            paragraph.append(line.strip())

    flush_paragraph()
    close_list()
    parts.append("</body></html>")
    return "\n".join(parts) + "\n"


def _inline(text: str) -> str:
    """Apply a small Markdown-inline subset without mangling snake_case identifiers."""
    placeholders: list[str] = []

    def stash(match: re.Match[str]) -> str:
        placeholders.append(match.group(0))
        return f"\x00PH{len(placeholders) - 1}\x00"

    # Protect code spans and links before emphasis rewrites.
    protected = re.sub(r"`[^`]+`", stash, text)
    protected = re.sub(r"\[[^\]]+\]\(https?://[^)]+\)", stash, protected)

    escaped = html.escape(protected)
    escaped = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", escaped)
    escaped = re.sub(r"(?<!\*)\*(.+?)\*(?!\*)", r"<em>\1</em>", escaped)
    # Italic underscores only when flanked by word boundaries (not snake_case).
    escaped = re.sub(r"(?<!\w)_([^_]+)_(?!\w)", r"<em>\1</em>", escaped)

    def restore(match: re.Match[str]) -> str:
        raw = placeholders[int(match.group(1))]
        if raw.startswith("`") and raw.endswith("`"):
            return f"<code>{html.escape(raw[1:-1])}</code>"
        link = re.match(r"\[([^\]]+)\]\((https?://[^)]+)\)", raw)
        if link:
            return (
                f'<a href="{html.escape(link.group(2), quote=True)}">'
                f"{html.escape(link.group(1))}</a>"
            )
        return html.escape(raw)

    return re.sub(r"\x00PH(\d+)\x00", restore, escaped)


def _build_mailto(subject: str, body: str, to: str = "") -> str:
    # Keep mailto under common URL length limits; truncate body if needed.
    max_body = 1500
    trimmed = body if len(body) <= max_body else body[: max_body - 20] + "\n\n[…truncated]"
    query = f"subject={quote(subject)}&body={quote(trimmed)}"
    return f"mailto:{to}?{query}"


def _buttondown_markdown(markdown: str) -> str:
    """Buttondown-friendly Markdown (no YAML frontmatter — API rejects it)."""
    return markdown.strip() + "\n"


def create_buttondown_draft(subject: str, body: str, api_key: str) -> dict:
    """Create a Buttondown email with status=draft only — never publish/send."""
    headers = {
        "Authorization": f"Token {api_key}",
        "Content-Type": "application/json",
    }
    payload = {
        "subject": subject,
        "body": body,
        "status": "draft",
    }
    with httpx.Client(timeout=30.0) as client:
        response = client.post(BUTTONDOWN_API, headers=headers, json=payload)
        response.raise_for_status()
        return response.json()


def export_digest(
    out_dir: Path,
    digest_name: str | None = None,
    *,
    i_approved: bool = False,
    mailto_to: str = "",
) -> dict[str, Path | str | None]:
    """
    Write free export artifacts for an *approved* digest.

    Never sends email. Optional Buttondown draft creation requires both
    BUTTONDOWN_API_KEY and the explicit email gate (APPROVED=1 or --i-approved).
    """
    digest_path = resolve_digest(out_dir, digest_name)
    if not is_approved(digest_path, out_dir):
        raise PermissionError(
            f"Digest is not approved yet: {digest_path.name}\n"
            "Run:  PYTHONPATH=src python -m niche_digest approve\n"
            "No files were written and nothing was emailed."
        )

    markdown = digest_path.read_text(encoding="utf-8")
    subject = _extract_subject(markdown, fallback=digest_path.stem)
    dest = export_dir(out_dir)
    dest.mkdir(parents=True, exist_ok=True)

    html_path = dest / "email-draft.html"
    mailto_path = dest / "mailto.txt"
    buttondown_md_path = dest / "buttondown.md"

    html_path.write_text(_markdown_to_html(markdown), encoding="utf-8")
    mailto_path.write_text(
        _build_mailto(subject, markdown, to=mailto_to) + "\n",
        encoding="utf-8",
    )
    buttondown_md_path.write_text(_buttondown_markdown(markdown), encoding="utf-8")

    result: dict[str, Path | str | None] = {
        "digest": digest_path,
        "html": html_path,
        "mailto": mailto_path,
        "buttondown_md": buttondown_md_path,
        "buttondown_id": None,
        "buttondown_skipped": None,
    }

    api_key = os.environ.get("BUTTONDOWN_API_KEY", "").strip()
    if not api_key:
        result["buttondown_skipped"] = "BUTTONDOWN_API_KEY not set — local files only"
        return result

    if not email_gate_ok(i_approved):
        result["buttondown_skipped"] = (
            "BUTTONDOWN_API_KEY is set, but email gate is closed. "
            "Re-run with APPROVED=1 or --i-approved to create a Buttondown *draft* only."
        )
        return result

    data = create_buttondown_draft(subject, _buttondown_markdown(markdown), api_key)
    result["buttondown_id"] = str(data.get("id") or data.get("api_url") or "created")
    return result
