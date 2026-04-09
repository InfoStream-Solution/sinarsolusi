# news_scraper

`news_scraper` is a modular scraping workspace built around site classes.

## Setup

```bash
cd apps/news_scraper
uv sync
cp .env.example .env
```

Set `SEED_DIR`, `LINKS_DIR`, `SCRAPED_DIR`, and `CONTENT_DIR` in `.env` to control where output is written.
Keep host mount paths in `compose.env`, not in the app `.env`.

Retention behavior is controlled with scraper-specific env vars:

```env
SCRAPER_DEBUG=0
KEEP_SEED=0
KEEP_SCRAPED=0
```

Defaults:
- `SCRAPER_DEBUG=1` implies keep intermediate files unless overridden
- `KEEP_SEED=1` keeps seed HTML
- `KEEP_SCRAPED=1` keeps raw article HTML

CLI flags override env:
- `--keep-seed` / `--no-keep-seed`
- `--keep-scraped` / `--no-keep-scraped`

## Run Seeder

```bash
uv run seed kompas.com
```

Seeder flow:
- run `nscraper` for the site's `start_url`
- write the seed file to `SEED_DIR/<domain>.seed`
- parse internal links from the seed content
- normalize links before writing them:
  - strip fragments and irrelevant query params
  - canonicalize article URLs where the site supports it
- write JSONL link records to `LINKS_DIR/<domain>.jsonl`
- remove the intermediate seed file by default

Keep the seed file when needed:

```bash
uv run seed --keep-seed kompas.com
```

Or via env:

```bash
KEEP_SEED=1 uv run seed kompas.com
```

Each JSONL line has:

```json
{"url": "https://kompas.com/...", "scraped": false}
```

## Extract News

```bash
uv run extract-news kompas.com
```

This command:
- reads `LINKS_DIR/<domain>.jsonl`
- keeps only URLs recognized as article URLs by the site class
- scrapes each article URL and stores the raw HTML in:

```text
SCRAPED_DIR/<domain>/article_html/<slug>.html
```

- reads the stored HTML back through the site parser
- writes one structured parsed file per article to:

```text
CONTENT_DIR/news_article/<domain>/<slug>.json
```

- and writes a readable Markdown companion to:

```text
CONTENT_DIR/news_article/<domain>/<slug>.md
```

- removes the intermediate scraped HTML files by default

Keep the raw article HTML when needed:

```bash
uv run extract-news --keep-scraped kompas.com
```

Or via env:

```bash
KEEP_SCRAPED=1 uv run extract-news kompas.com
```

If an article fails during extraction, the run continues and the failure is appended to:

```text
CONTENT_DIR/errors/<domain>/extract-news.jsonl
```

For Kompas, article URLs are recognized by the usual pattern:

```text
/.../read/YYYY/MM/DD/<id>/<title>
```

The parsed article model currently includes:
- `content_type`
- `title`
- `url`
- `source_site`
- `category`
- `published_at`
- `author`
- `summary`
- `content`
- `word_count`
- `char_count`
- `scraped_at`

## Container

Build from `apps/news_scraper`:

```bash
docker build -t news-scraper .
```

Run with host-mounted persistent data:

```bash
docker run --rm \
  -e SEED_DIR=/data/seed \
  -e LINKS_DIR=/data/links \
  -e SCRAPED_DIR=/data/scraped \
  -e CONTENT_DIR=/data/content \
  -v /var/lib/sinarsolusi/seed:/data/seed \
  -v /var/lib/sinarsolusi/links:/data/links \
  -v /var/lib/sinarsolusi/scraped:/data/scraped \
  -v /var/lib/sinarsolusi/content:/data/content \
  news-scraper seed kompas.com
```

Or with Compose:

```bash
cp compose.env.example compose.env
docker compose --env-file compose.env run --rm news-scraper seed kompas.com
```

Run other entrypoints the same way:

```bash
docker compose --env-file compose.env run --rm news-scraper seed kompas.com
docker compose --env-file compose.env run --rm news-scraper extract-news kompas.com
```

## Site Model

Each supported site extends `BaseSite`.

Current example:
- `kompas.com` -> [`KompasComSite`](/home/ubuntu/projects/sinarsolusi/apps/news_scraper/src/sites/kompas_com.py)

`BaseSite` provides:
- `start_url`
- `output_path`
- `default_nscrape_options`
- `scrape()`

Default `nscraper` options include:
- `transform = "basic"`
- `pretty = true`
- default HTML headers
