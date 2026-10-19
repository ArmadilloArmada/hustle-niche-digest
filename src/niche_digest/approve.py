from __future__ import annotations

import json
import shutil
from datetime import datetime, timezone
from pathlib import Path


DIGEST_GLOB = "digest-*.md"


def list_digests(out_dir: Path) -> list[Path]:
    """Return digest markdown files in out_dir, newest-looking name last."""
    files = sorted(out_dir.glob(DIGEST_GLOB))
    return [p for p in files if p.is_file()]


def resolve_digest(out_dir: Path, name: str | None = None) -> Path:
    """Resolve a digest path: explicit name/path, or the latest digest-*.md."""
    if name:
        candidate = Path(name)
        if not candidate.is_absolute():
            # Allow bare filename, digest-DATE, or relative path.
            for option in (
                candidate,
                out_dir / candidate.name,
                out_dir / f"{candidate.name}.md" if not candidate.name.endswith(".md") else None,
            ):
                if option is not None and option.is_file():
                    return option.resolve()
        elif candidate.is_file():
            return candidate.resolve()
        raise FileNotFoundError(f"Digest not found: {name}")

    digests = list_digests(out_dir)
    if not digests:
        raise FileNotFoundError(
            f"No {DIGEST_GLOB} under {out_dir}. Run the digest pipeline first."
        )
    return digests[-1].resolve()


def approved_dir(out_dir: Path) -> Path:
    return out_dir / "approved"


def sidecar_path(digest_path: Path) -> Path:
    return digest_path.with_suffix(digest_path.suffix + ".approved")


def approved_copy_path(out_dir: Path, digest_path: Path) -> Path:
    return approved_dir(out_dir) / digest_path.name


def is_approved(digest_path: Path, out_dir: Path | None = None) -> bool:
    """True if sidecar stamp or approved/ copy exists for this digest."""
    base = out_dir or digest_path.parent
    if sidecar_path(digest_path).is_file():
        return True
    copy = approved_copy_path(base, digest_path)
    return copy.is_file()


def approve_digest(digest_path: Path, out_dir: Path | None = None) -> tuple[Path, Path]:
    """
    Mark a digest approved: copy into out/approved/ and write a .approved sidecar.

    Returns (approved_copy_path, sidecar_path).
    """
    digest_path = digest_path.resolve()
    if not digest_path.is_file():
        raise FileNotFoundError(f"Digest not found: {digest_path}")

    base = out_dir or digest_path.parent
    dest_dir = approved_dir(base)
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest = approved_copy_path(base, digest_path)
    shutil.copy2(digest_path, dest)

    try:
        approved_rel = str(dest.relative_to(base.resolve()))
    except ValueError:
        approved_rel = str(dest)
    stamp = {
        "approved_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "source": digest_path.name,
        "approved_copy": approved_rel,
    }
    side = sidecar_path(digest_path)
    side.write_text(json.dumps(stamp, indent=2) + "\n", encoding="utf-8")
    return dest, side
