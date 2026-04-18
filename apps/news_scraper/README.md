# news_scraper

`news_scraper` is a `uv`-managed scraping workspace for site-specific seed crawling, article extraction, and downstream posting.

Supported sites:
- `kompas.com`
- `detik.com`
- `beritasatu.com`

Quick start:

```bash
uv sync
cp .env.example .env
```

Common commands:

```bash
uv run seed kompas.com
uv run extract-news kompas.com
uv run scrape kompas.com -u https://example.com/article
uv run post-news kompas.com
```

For the detailed workflow, environment variables, container setup, and agent-facing repo instructions, see [`AGENTS.md`](AGENTS.md).
