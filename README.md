# sinarsolusi

This repository is now structured to support future monorepo growth.

The current production website lives in `apps/website`.
The first Python service scaffold lives in `apps/news_scraper`.

## Current app

- Public marketing website: `apps/website`
- News scraper scaffold: `apps/news_scraper`

## Local development

Run commands from `apps/website`:

```bash
cd apps/website
npm install
npm run dev
```

Use Node.js `24.14.1` or another Node 24 release that satisfies `apps/website/package.json`.

For the scraper app:

```bash
cd apps/news_scraper
uv sync
uv run nscraper --source example
```

## Deployment

For Vercel, set the project Root Directory to `apps/website`.
