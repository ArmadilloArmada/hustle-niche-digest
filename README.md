# hustle-niche-digest

Indie / SaaS **developer-tools changelog** niche digest.

Pipeline: **fetch public RSS/Atom → dedupe & rank → draft digest → write `out/`** for human approval. Nothing is emailed or published automatically.

## Requirements

- Python 3.11+
- Network access to the RSS/Atom URLs in your config
- Optional: `OPENAI_API_KEY` for LLM drafting (template draft works without it)

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
# or after `pip install -e .`:
niche-digest
```

Useful flags:

```bash
PYTHONPATH=src python -m niche_digest --config config.yaml --out-dir out
PYTHONPATH=src python -m niche_digest --date 2026-10-19
```

## Output

Each run writes:

```text
out/digest-YYYY-MM-DD.md
```

Review and edit that file offline, then paste into Substack / Beehiiv / Buttondown (or anywhere you publish). **This tool does not send email.**

## Environment variables

| Variable | Required | Purpose |
|----------|----------|---------|
| `OPENAI_API_KEY` | No | If set, draft the digest with OpenAI; otherwise a deterministic template draft is used |
| `OPENAI_MODEL` | No | Model name (default: `gpt-4o-mini`) |

## Compliance

- **Public RSS/Atom only.** Do not add scrapers that ignore robots.txt or site ToS.
- Prefer short summaries + links; avoid long verbatim quotes from release notes in paid products without review.
- You own CAN-SPAM / consent for any list you eventually send to—this CLI never cold-adds subscribers.
- Attribution: keep source links in the digest so readers can open the original changelog.

## Layout

```text
config.example.yaml
src/niche_digest/          # CLI + pipeline
out/                       # human-approved drafts land here
requirements.txt
pyproject.toml
```

## License

MIT — use at your own risk for research/demo workflows.
