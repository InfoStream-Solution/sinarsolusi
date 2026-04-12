# news_scraper

`news_scraper` is a `uv`-managed scraping workspace for site-specific seed crawling and article extraction.

Current supported site:
- `kompas.com`
- `detik.com`
- `beritasatu.com`

Current workflow:
1. `seed` fetches the site entry page and builds a normalized internal-link queue.
2. `extract-news` reads that queue, keeps only article URLs, scrapes each article, and writes parsed output.
3. `scrape` fetches and parses one article URL directly.
4. `group-news` loads all extracted articles, groups similar stories, and writes a local SQLite index with `group_id`.
5. `post-news` reads parsed article JSON and posts it to the KBT API.

This app is intentionally small and site-driven:
- site behavior lives under [`src/sites`](src/sites)
- generic pipeline behavior lives under [`src/seed.py`](src/seed.py) and [`src/extract_news.py`](src/extract_news.py)
- single-article scraping lives under [`src/scrape.py`](src/scrape.py)
- raw fetches are done through `nscraper`
- Kompas article parsing currently uses `justhtml` against `nscraper` output with `transform="basic"`
- Detik article parsing currently uses `justhtml` against standard detik article pages
- BeritaSatu article parsing currently uses `justhtml` against standard BeritaSatu article pages

## Layout

```text
apps/news_scraper/
├── Dockerfile
├── pyproject.toml
├── .env.example
└── src/
    ├── config.py
    ├── extract_news.py
    ├── links.py
    ├── models.py
    ├── paths.py
    ├── seed.py
    ├── scrape.py
    ├── group_news.py
    ├── site_loader.py
    ├── sites/
    │   ├── base.py
    │   ├── beritasatu_com.py
    │   ├── detik_com.py
    │   └── kompas_com.py
    └── utils/
        └── logging.py
```

## Setup

```bash
cd apps/news_scraper
uv sync
cp .env.example .env
```

Recommended local `.env`:

```env
SEED_DIR=.data/seed
LINKS_DIR=.data/links
SCRAPED_DIR=.data/scraped
CONTENT_DIR=.data/content
SCRAPER_DEBUG=0
KEEP_SEED=0
KEEP_SCRAPED=0
KBT_API_BASE_URL=http://127.0.0.1:8000
KBT_API_TOKEN=your-token-here
```

Important split:
- app `.env` is for Python runtime paths and scraper behavior
- `compose.env` is for host mount paths used by Docker Compose

Retention controls:
- `SCRAPER_DEBUG=1` makes retention default to on unless overridden
- `KEEP_SEED=1` keeps intermediate seed HTML
- `KEEP_SCRAPED=1` keeps intermediate article HTML

CLI flags override env:
- `--keep-seed` / `--no-keep-seed`
- `--keep-scraped` / `--no-keep-scraped`

KBT posting uses:
- `KBT_API_BASE_URL` for the API root
- `KBT_API_TOKEN` for `Authorization: Token ...`

## Commands

Current entrypoints:

```bash
uv run seed kompas.com
uv run extract-news kompas.com
uv run scrape kompas.com -u https://nasional.kompas.com/read/2026/04/11/13541301/kenakan-beskap-dan-peci-hitam-prabowo-hadiri-munas-xvi-pb-ipsi
uv run group-news kompas.com
uv run post-news kompas.com
uv run post-news --dry-run kompas.com
```

Rebuild and inspect grouped articles in one step:

```bash
bash scripts/rebuild_and_select.sh kompas.com
```

Tests:

```bash
uv run --extra test pytest
uv run --extra test pytest --cov=src --cov-report=term-missing
```

Lint:

```bash
uv sync --extra lint
uv run ruff check .
```

The intended pipeline is:
1. seed
2. extract-news
3. scrape
4. group-news
5. post-news

Dry run mode validates the outbound payloads without calling the API or writing
posted markers.

Single article output uses the same location as `extract-news`.

Grouping output is stored at:

```text
CONTENT_DIR/news_group/news_group.sqlite3
```

Each grouped article keeps a persistent `group_id` for downstream topic
transformation work.

## Seed

```bash
uv run seed kompas.com
```

What `seed` does:
- loads the site class through [`site_loader.py`](src/site_loader.py)
- runs `nscraper` against the site `start_url`
- writes the fetched seed content to:

```text
SEED_DIR/<domain>.seed
```

- extracts internal links from the seed content
- normalizes links before writing them:
  - strips fragments
  - normalizes article URLs with site rules
- writes the queue to:

```text
LINKS_DIR/<domain>.jsonl
```

- removes the intermediate `.seed` file by default

Keep the seed file:

```bash
uv run seed --keep-seed kompas.com
```

Queue format:

```json
{"url": "https://kompas.com/...", "scraped": false}
```

For Kompas, article links are canonicalized during seeding so queue entries are stable.

Example:
- input:
  - `https://www.kompas.com/edu/read/...?...source=terpopuler`
- normalized queue URL:
  - `https://www.kompas.com/edu/read/...?...page=all`

## Extract News

```bash
uv run extract-news kompas.com
```

What `extract-news` does:
- reads `LINKS_DIR/<domain>.jsonl`
- keeps only pending URLs recognized as article URLs by the site class
- canonicalizes article URLs before scraping
- scrapes each article with `nscraper`
- stores raw article HTML at:

```text
SCRAPED_DIR/<domain>/article_html/<slug>.html
```

- reads the stored HTML back
- parses it through the site parser
- writes structured output to:

```text
CONTENT_DIR/news_article/<domain>/<slug>.json
```

- writes a human-readable verification file to:

```text
CONTENT_DIR/news_article/<domain>/<slug>.md
```

- marks successfully processed links as scraped in the queue
- removes intermediate article HTML by default

Keep raw article HTML:

```bash
uv run extract-news --keep-scraped kompas.com
```

Limit the run:

```bash
uv run extract-news --limit 10 kompas.com
```

## Parsed Output

Parsed content is stored as JSON and Markdown.

Current parsed model fields:
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

The Markdown file exists only to make parser verification easier. JSON is the machine-facing output.

Example parsed JSON shape:

```json
{
  "content_type": "news_article",
  "title": "Example title",
  "url": "https://www.kompas.com/example/read/2026/04/09/123456789/example-title?page=all",
  "source_site": "kompas.com",
  "category": "Tren",
  "published_at": "09/04/2026, 21:30 WIB",
  "author": "Example Author",
  "summary": "Lead paragraph text.",
  "content": "Lead paragraph text.\n\nSecond paragraph text.",
  "word_count": 120,
  "char_count": 860,
  "scraped_at": "2026-04-09T22:00:00+07:00"
}
```

## Site Model

Each supported site extends [`BaseSite`](src/sites/base.py).

`BaseSite` currently provides:
- `domain`
- `start_url`
- `allowed_hosts`
- `article_path_patterns`
- `default_nscrape_options`
- `normalize_url()`
- `normalize_article_url()`
- `scrape()`
- `scrape_article()`
- `parse_article()`
- `save_parsed_article()`

The site class owns:
- which hosts count as internal
- which URL paths count as article URLs
- how article URLs are canonicalized
- how article HTML is parsed and cleaned

Current Kompas implementation:
- [`KompasComSite`](src/sites/kompas_com.py)
- [`DetikComSite`](src/sites/detik_com.py)
- [`BeritasatuComSite`](src/sites/beritasatu_com.py)

Kompas-specific behavior currently includes:
- canonicalizing article URLs to `?page=all`
- removing tracking-style query noise
- extracting metadata and body from `justhtml` output
- removing known non-content lines such as:
  - `Penulis: ...`
  - `Baca juga: ...`
  - `(Sumber: ...)`
  - `Artikel ini pernah tayang ...`

## Add A Site

To add another site, create a new site class under [`src/sites`](src/sites).

Minimum steps:
1. Add a new file such as:
   - [`src/sites/example_com.py`](src/sites/example_com.py)
2. Create a class extending [`BaseSite`](src/sites/base.py)
3. Define:
   - `domain`
   - `start_url`
   - `allowed_hosts`
   - `article_path_patterns`
4. Implement:
   - `parse_article(html, url)`
5. Make sure the loader can resolve the new domain through [`site_loader.py`](src/site_loader.py)

Typical responsibilities for a site class:
- identify which links are internal
- identify which URLs are article URLs
- canonicalize article URLs
- extract article metadata and body
- remove site-specific noise

Good rule of thumb:
- keep generic pipeline behavior in `BaseSite`
- keep publisher-specific parsing and cleanup in the site file

Suggested implementation order for a new site:
1. make `seed` produce a good link queue
2. make `extract-news` recognize article URLs correctly
3. make `parse_article()` produce clean JSON/Markdown
4. only then add more cleanup rules

Minimal skeleton:

```python
from __future__ import annotations

from dataclasses import dataclass
import re

from ..config import Settings
from ..models import ParsedContent
from .base import BaseSite


ARTICLE_PATH_PATTERNS = (
    re.compile(r"^/news/\d+/.+$"),
)


@dataclass
class ExampleComSite(BaseSite):
    settings: Settings

    def __init__(self, settings: Settings) -> None:
        super().__init__(
            settings=settings,
            domain="example.com",
            start_url="https://example.com",
            allowed_hosts={"example.com", "www.example.com"},
            article_path_patterns=ARTICLE_PATH_PATTERNS,
        )

    def normalize_article_url(self, url: str) -> str:
        return self.normalize_url(url)

    def parse_article(self, html: str, url: str) -> ParsedContent:
        title = "Replace me"
        content = "Replace me"
        summary = content
        return self.default_parsed_content(
            title=title,
            url=url,
            category=None,
            author=None,
            published_at=None,
            summary=summary,
            content=content,
        )
```

Then wire it into the loader and verify:

```bash
uv run seed example.com
uv run extract-news --limit 1 example.com
```

## Logging

Logging is stdout-based and intended for local runs and containers.

Command loggers:
- `seed`
- `extract-news`
- `site_loader`

Site loggers:
- `site.<domain>`
- example: `site.kompas.com`

`SCRAPER_DEBUG=1` switches logging to debug level and also changes retention defaults unless overridden.

Failures during `extract-news` do not stop the whole run. Each article failure is logged and appended to:

```text
CONTENT_DIR/errors/<domain>/extract-news.jsonl
```

Each error record includes:
- `occurred_at`
- `domain`
- `command`
- `original_url`
- `article_url`
- `error_type`
- `error_message`

## Container

Build the container image from the repo root:

```bash
docker build -t news-scraper -f apps/news_scraper/Dockerfile apps/news_scraper
```

The production image runs the app commands directly. Use `seed` or `extract-news` as the container command.

So in containers you run commands like:

```bash
docker run --rm \
  -v /var/lib/sinarsolusi/seed:/data/seed \
  -v /var/lib/sinarsolusi/links:/data/links \
  -v /var/lib/sinarsolusi/scraped:/data/scraped \
  -v /var/lib/sinarsolusi/content:/data/content \
  news-scraper seed kompas.com
```

Or:

```bash
docker run --rm \
  -v /var/lib/sinarsolusi/seed:/data/seed \
  -v /var/lib/sinarsolusi/links:/data/links \
  -v /var/lib/sinarsolusi/scraped:/data/scraped \
  -v /var/lib/sinarsolusi/content:/data/content \
  news-scraper extract-news kompas.com
```

Use this section for local container smoke tests. For devops/runtime and Compose-based server runs, see [`devops/README.md`](../../devops/README.md).

## Troubleshooting

Common issues and fixes:

### Parser still includes noise

If article content still includes unwanted lines for Kompas:
- update [`src/sites/kompas_com.py`](src/sites/kompas_com.py)
- tighten the cleanup rules in the site parser
- rerun:

```bash
uv run extract-news --keep-scraped --limit 1 kompas.com
```

Keeping the scraped HTML for one run makes parser debugging much easier.

### Container does not reflect code changes

If you changed parser logic or command behavior and the container still behaves like the old version, rebuild the image:

```bash
docker build --no-cache -t news-scraper -f apps/news_scraper/Dockerfile apps/news_scraper
```

Then rerun the command.

### `seed` or `extract-news` paths look wrong

For local `uv run` development, check `.env` for:
- `SEED_DIR`
- `LINKS_DIR`
- `SCRAPED_DIR`
- `CONTENT_DIR`

For containerized runs, check `devops/runtime/news_scraper.compose.yaml` and the host mount paths used by the runtime scripts.

### Queue contains article variants or tracking params

This is handled by site-level canonicalization. If a site still writes unstable URLs into the queue:
- update `normalize_article_url()` in that site class
- rerun `seed`
