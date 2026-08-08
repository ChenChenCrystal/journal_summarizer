# journal_summarizer

Automated daily collection + AI summarization for papers relevant to **HCI/CMC in advertising and communication**.

## What this currently does

- Collects papers from the **arXiv API** (not brittle website scraping).
- Focuses on topics including:
  - attention
  - cognitive offloading
  - generative AI
  - virtual reality
  - advertising/marketing communication
- Generates:
  - `summaries/articles_YYYY-MM-DD.json`
  - `summaries/articles_YYYY-MM-DD.md`
- Optionally adds AI summaries when `OPENAI_API_KEY` is available.

## Why API-first instead of “scraping bypass”

Some journal sites block automated scraping or disallow it in their terms. This project is configured to use compliant APIs (arXiv) so your pipeline remains stable and policy-friendly.

If you want broader coverage, next safest additions are:
- OpenAlex API
- Semantic Scholar API
- Crossref API

## Local run

```bash
python scraper.py --max-results 30
```

If you set `OPENAI_API_KEY`, summaries are generated with `OPENAI_MODEL` (default: `gpt-4o-mini`).

## GitHub Actions

Workflow: `.github/workflows/scrape-articles.yml`

- Runs daily at 09:00 UTC.
- Commits new summary files under `summaries/`.
