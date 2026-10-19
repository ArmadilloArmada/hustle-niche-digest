# hustle-niche-digest

Indie / SaaS **developer-tools changelog** niche digest.

Pipeline: **fetch public RSS/Atom → dedupe & rank → draft digest → human approve → export** for paste/send. Nothing is emailed or published automatically.

## Requirements

- Python 3.11+
- Network access to the RSS/Atom URLs in your config
- Optional: `OPENAI_API_KEY` for LLM drafting (template draft works without it)
- Optional: `BUTTONDOWN_API_KEY` to create a **draft** only in Buttondown (never publish/send from this CLI)

## Install

```bash
python3 -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
# or: pip install -e .
```

## Configure

```bash
cp config.example.yaml config.yaml
```

Edit `config.yaml` to change the niche name, `max_items`, or the fixed feed list. Feeds must be **public RSS/Atom** (this MVP ships GitHub Releases Atom URLs for popular developer tools).

## Run

From the repo root:

```bash
PYTHONPATH=src python -m niche_digest
# or explicitly:
PYTHONPATH=src python -m niche_digest run
# or after `pip install -e .`:
niche-digest run
```

Useful flags:

```bash
PYTHONPATH=src python -m niche_digest run --config config.yaml --out-dir out
PYTHONPATH=src python -m niche_digest run --date 2026-10-19
```

Each run writes:

```text
out/digest-YYYY-MM-DD.md
```

## Approve → Export → (optional) paste

**Nothing is emailed unless you explicitly approve, then optionally open a gate for ESP draft creation.** Default free path only writes local files you can paste into Substack / Buttondown / Beehiiv.

### 1. Approve

Mark the latest (or a named) digest as approved. This copies it to `out/approved/` and writes a `.approved` sidecar stamp:

```bash
PYTHONPATH=src python -m niche_digest approve
PYTHONPATH=src python -m niche_digest approve --digest digest-2026-10-19.md
```

### 2. Export (free path — no email)

Requires an approved digest. Writes:

```text
out/export/email-draft.html
out/export/mailto.txt
out/export/buttondown.md
```

```bash
PYTHONPATH=src python -m niche_digest export
# alias:
PYTHONPATH=src python -m niche_digest send-draft
```

Open `mailto.txt` in a browser/mail client, or paste `buttondown.md` / `email-draft.html` into your newsletter tool.

### 3. Optional Buttondown draft (still not a send)

If `BUTTONDOWN_API_KEY` is set, create a Buttondown email with **`status=draft` only** after an extra explicit gate:

```bash
APPROVED=1 PYTHONPATH=src python -m niche_digest export
# or:
PYTHONPATH=src python -m niche_digest export --i-approved
```

Without `APPROVED=1` / `--i-approved`, local export files are still written; the API call is skipped. This CLI never sets `about_to_send` or publishes.

## Environment variables

| Variable | Required | Purpose |
|----------|----------|---------|
| `OPENAI_API_KEY` | No | If set, draft the digest with OpenAI; otherwise a deterministic template draft is used |
| `OPENAI_MODEL` | No | Model name (default: `gpt-4o-mini`) |
| `BUTTONDOWN_API_KEY` | No | If set **and** `APPROVED=1` / `--i-approved`, create a Buttondown **draft** only |
| `APPROVED` | No | Set to `1` to open the ESP draft gate (same as `--i-approved`) |

## Weekly schedule (GitHub Actions)

Every Monday at **14:05 UTC**, [`.github/workflows/weekly-niche-digest.yml`](.github/workflows/weekly-niche-digest.yml) runs a **draft-only** pipeline and uploads artifact **`niche-digest-draft`** (no approve/export/send). Download from the Actions run → **Artifacts**, unzip into `out/`, then approve + export locally.

## Compliance

- **Public RSS/Atom only.** Do not add scrapers that ignore robots.txt or site ToS.
- Prefer short summaries + links; avoid long verbatim quotes from release notes in paid products without review.
- **No cold spam.** You own CAN-SPAM / consent for any list you eventually send to—this CLI never cold-adds subscribers and never auto-sends.
- Human approve is mandatory before export; ESP draft creation needs a second explicit gate.
- Attribution: keep source links in the digest so readers can open the original changelog.

## Layout

```text
config.example.yaml
src/niche_digest/          # CLI + pipeline + approve/export
out/                       # drafts land here
out/approved/              # human-approved copies
out/export/                # free send/export artifacts
requirements.txt
pyproject.toml
```

## License

MIT — use at your own risk for research/demo workflows.
