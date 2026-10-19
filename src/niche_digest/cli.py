from __future__ import annotations

import argparse
from datetime import date
from pathlib import Path

from niche_digest.pipeline import run


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="niche-digest",
        description="Fetch public RSS changelogs, rank them, and draft a digest under out/.",
    )
    parser.add_argument(
        "--config",
        type=Path,
        default=Path("config.yaml"),
        help="Path to config.yaml (default: ./config.yaml)",
    )
    parser.add_argument(
        "--out-dir",
        type=Path,
        default=Path("out"),
        help="Output directory (default: ./out)",
    )
    parser.add_argument(
        "--date",
        type=str,
        default=None,
        help="Issue date YYYY-MM-DD (default: today)",
    )
    args = parser.parse_args(argv)

    issue_date = date.fromisoformat(args.date) if args.date else None
    out_path = run(args.config, args.out_dir, issue_date=issue_date)
    print(f"Wrote {out_path}")
    print("Human approve offline — nothing was emailed or published.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
