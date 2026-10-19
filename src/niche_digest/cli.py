from __future__ import annotations

import argparse
import sys
from datetime import date
from pathlib import Path

from niche_digest.approve import approve_digest, resolve_digest
from niche_digest.export import export_digest
from niche_digest.pipeline import run


def _add_out_dir(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--out-dir",
        type=Path,
        default=Path("out"),
        help="Output directory (default: ./out)",
    )


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="niche-digest",
        description=(
            "Fetch public RSS changelogs, draft a digest under out/, "
            "then approve + export for human send (never auto-email)."
        ),
    )
    sub = parser.add_subparsers(dest="command")

    run_p = sub.add_parser(
        "run",
        help="Fetch → rank → draft digest markdown under out/",
    )
    run_p.add_argument(
        "--config",
        type=Path,
        default=Path("config.yaml"),
        help="Path to config.yaml (default: ./config.yaml)",
    )
    _add_out_dir(run_p)
    run_p.add_argument(
        "--date",
        type=str,
        default=None,
        help="Issue date YYYY-MM-DD (default: today)",
    )

    approve_p = sub.add_parser(
        "approve",
        help="Mark latest (or named) out/digest-*.md as approved",
    )
    _add_out_dir(approve_p)
    approve_p.add_argument(
        "--digest",
        "-d",
        type=str,
        default=None,
        help="Digest filename or path (default: latest out/digest-*.md)",
    )

    export_p = sub.add_parser(
        "export",
        aliases=["send-draft"],
        help=(
            "Write free export files for an approved digest. "
            "Never emails; optional Buttondown draft needs APPROVED=1 or --i-approved."
        ),
    )
    _add_out_dir(export_p)
    export_p.add_argument(
        "--digest",
        "-d",
        type=str,
        default=None,
        help="Digest filename or path (default: latest out/digest-*.md)",
    )
    export_p.add_argument(
        "--i-approved",
        action="store_true",
        help=(
            "Explicit email-gate confirmation (same as APPROVED=1). "
            "Required to create a Buttondown draft when BUTTONDOWN_API_KEY is set."
        ),
    )
    export_p.add_argument(
        "--mailto-to",
        type=str,
        default="",
        help="Optional To: address embedded in mailto.txt (default: empty)",
    )

    return parser


def _normalize_argv(argv: list[str] | None) -> list[str]:
    """Treat bare flags as `run` so `python -m niche_digest --config …` still works."""
    args = list(sys.argv[1:] if argv is None else argv)
    known = {"run", "approve", "export", "send-draft", "-h", "--help"}
    if not args or args[0] not in known:
        return ["run", *args]
    return args


def cmd_run(args: argparse.Namespace) -> int:
    issue_date = date.fromisoformat(args.date) if args.date else None
    out_path = run(args.config, args.out_dir, issue_date=issue_date)
    print(f"Wrote {out_path}")
    print("Human approve offline — nothing was emailed or published.")
    print(f"Next: PYTHONPATH=src python -m niche_digest approve --out-dir {args.out_dir}")
    return 0


def cmd_approve(args: argparse.Namespace) -> int:
    digest = resolve_digest(args.out_dir, args.digest)
    approved_copy, sidecar = approve_digest(digest, args.out_dir)
    print(f"Approved {digest.name}")
    print(f"  copy:    {approved_copy}")
    try:
        side_disp = sidecar.relative_to(Path.cwd())
    except ValueError:
        side_disp = sidecar
    print(f"  sidecar: {side_disp}")
    print("Nothing was emailed. Export with:")
    print(f"  PYTHONPATH=src python -m niche_digest export --out-dir {args.out_dir}")
    return 0


def cmd_export(args: argparse.Namespace) -> int:
    try:
        result = export_digest(
            args.out_dir,
            args.digest,
            i_approved=args.i_approved,
            mailto_to=args.mailto_to,
        )
    except PermissionError as exc:
        print(str(exc), file=sys.stderr)
        return 2

    print(f"Export from approved digest: {result['digest']}")
    print(f"  HTML:          {result['html']}")
    print(f"  mailto:        {result['mailto']}")
    print(f"  Buttondown MD: {result['buttondown_md']}")
    if result.get("buttondown_id"):
        print(f"  Buttondown draft id: {result['buttondown_id']} (status=draft only)")
    elif result.get("buttondown_skipped"):
        print(f"  Buttondown: {result['buttondown_skipped']}")
    print("No email was sent. Paste into Substack/Buttondown or open mailto.txt.")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(_normalize_argv(argv))
    if args.command in (None, "run"):
        return cmd_run(args)
    if args.command == "approve":
        return cmd_approve(args)
    if args.command in ("export", "send-draft"):
        return cmd_export(args)
    parser.print_help()
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
