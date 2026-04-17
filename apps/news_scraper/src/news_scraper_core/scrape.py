from __future__ import annotations

import argparse
import json

from .config import get_settings
from .site_loader import load_site
from .utils import configure_logging, get_logger


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="scrape")
    parser.add_argument(
        "domain",
        help="Registered domain identifier, for example kompas.com.",
    )
    parser.add_argument(
        "-u",
        "--url",
        required=True,
        help="Single article URL to scrape.",
    )
    parser.add_argument(
        "--keep-scraped",
        action=argparse.BooleanOptionalAction,
        default=None,
        help="Keep the intermediate scraped HTML file after parsing the article.",
    )
    return parser

def main(argv: list[str] | None = None) -> None:
    parser = build_parser()
    args = parser.parse_args() if argv is None else parser.parse_args(argv[1:])

    settings = get_settings()
    configure_logging(debug=settings.scraper_debug)
    logger = get_logger("scrape")
    site = load_site(args.domain, settings=settings)
    article_url = site.normalize_article_url(args.url)
    keep_scraped = (
        settings.keep_scraped if args.keep_scraped is None else args.keep_scraped
    )

    if not site.is_article_url(article_url):
        raise SystemExit(f"{article_url!r} is not a valid article URL for {site.domain}")

    logger.info(
        "scrape_start domain=%r original_url=%r article_url=%r keep_scraped=%r",
        site.domain,
        args.url,
        article_url,
        keep_scraped,
    )

    html_path = site.scraped_article_output_path(article_url)
    try:
        site.scrape_article(article_url)
        html = html_path.read_text(encoding="utf-8")
        article = site.parse_article(html, article_url)
        parsed_path = site.save_parsed_article(article, article_url)
        markdown_path = site.article_markdown_output_path(article_url)
        if not keep_scraped and html_path.exists():
            html_path.unlink()
            logger.info(
                "scraped_file_removed domain=%r article_url=%r html_path=%r",
                site.domain,
                article_url,
                str(html_path),
            )
        payload = {
            "domain": site.domain,
            "original_url": args.url,
            "article_url": article_url,
            "json_path": str(parsed_path),
            "markdown_path": str(markdown_path),
            "keep_scraped": keep_scraped,
            "removed_scraped_file": not keep_scraped,
            "scraped_article_dir": str(site.scraped_article_dir()),
        }
        logger.info(
            "scrape_done domain=%r article_url=%r json_path=%r markdown_path=%r",
            site.domain,
            article_url,
            str(parsed_path),
            str(markdown_path),
        )
        print(json.dumps(payload, indent=2))
    except Exception:
        logger.exception("scrape_failed domain=%r article_url=%r", site.domain, article_url)
        raise


if __name__ == "__main__":
    main()
