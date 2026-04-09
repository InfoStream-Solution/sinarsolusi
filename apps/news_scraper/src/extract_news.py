from __future__ import annotations

import argparse
import json
from pathlib import Path

from .config import get_settings
from .links import mark_link_scraped, read_links
from .models import now_iso
from .paths import error_log_path, links_jsonl_path
from .site_loader import load_site
from .utils import configure_logging, get_logger


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="extract-news")
    parser.add_argument(
        "domain",
        help="Registered domain identifier, for example kompas.com.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=0,
        help="Maximum number of pending article URLs to scrape. 0 means no limit.",
    )
    parser.add_argument(
        "--keep-scraped",
        action=argparse.BooleanOptionalAction,
        default=None,
        help="Keep the intermediate scraped HTML files after parsing articles.",
    )
    return parser


def append_error_record(path: Path, record: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, ensure_ascii=False) + "\n")


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    settings = get_settings()
    configure_logging(debug=settings.scraper_debug)
    logger = get_logger("extract-news")
    site = load_site(args.domain, settings=settings)
    links_path = links_jsonl_path(settings.links_dir, site.domain)
    links = read_links(links_path)
    keep_scraped = (
        settings.keep_scraped if args.keep_scraped is None else args.keep_scraped
    )

    pending_article_links = [
        link for link in links if not link.scraped and site.is_article_url(link.url)
    ]
    if args.limit > 0:
        pending_article_links = pending_article_links[: args.limit]
    logger.info(
        "extract_news_start domain=%r links_path=%r pending_article_count=%d keep_scraped=%r",
        site.domain,
        str(links_path),
        len(pending_article_links),
        keep_scraped,
    )

    written_files: list[str] = []
    written_markdown_files: list[str] = []
    removed_scraped_files: list[str] = []
    error_path = error_log_path(settings.content_dir, site.domain, "extract-news")
    error_count = 0
    for link in pending_article_links:
        article_url = site.normalize_article_url(link.url)
        logger.info(
            "article_process_start domain=%r original_url=%r article_url=%r",
            site.domain,
            link.url,
            article_url,
        )
        try:
            site.scrape_article(article_url)
            html_path = site.scraped_article_output_path(article_url)
            html = html_path.read_text(encoding="utf-8")
            article = site.parse_article(html, article_url)
            parsed_path = site.save_parsed_article(article, article_url)
            markdown_path = site.article_markdown_output_path(article_url)
            if not keep_scraped and html_path.exists():
                html_path.unlink()
                removed_scraped_files.append(str(html_path))
                logger.info(
                    "scraped_file_removed domain=%r article_url=%r html_path=%r",
                    site.domain,
                    article_url,
                    str(html_path),
                )
            mark_link_scraped(links_path, link.url)
            logger.info(
                "article_process_done domain=%r original_url=%r article_url=%r json_path=%r markdown_path=%r",
                site.domain,
                link.url,
                article_url,
                str(parsed_path),
                str(markdown_path),
            )
            written_files.append(str(parsed_path))
            written_markdown_files.append(str(markdown_path))
        except Exception as exc:
            error_count += 1
            logger.exception(
                "article_process_failed domain=%r original_url=%r article_url=%r",
                site.domain,
                link.url,
                article_url,
            )
            append_error_record(
                error_path,
                {
                    "occurred_at": now_iso(),
                    "domain": site.domain,
                    "command": "extract-news",
                    "original_url": link.url,
                    "article_url": article_url,
                    "error_type": type(exc).__name__,
                    "error_message": str(exc),
                },
            )

    payload = {
        "domain": site.domain,
        "links_input_path": str(links_path),
        "article_count": len(pending_article_links),
        "written_files": written_files,
        "written_markdown_files": written_markdown_files,
        "keep_scraped": keep_scraped,
        "removed_scraped_files": removed_scraped_files,
        "scraped_article_dir": str(site.scraped_article_dir()),
        "error_log_path": str(error_path),
        "error_count": error_count,
    }
    logger.info(
        "extract_news_done domain=%r article_count=%d removed_scraped_count=%d error_count=%d",
        site.domain,
        len(pending_article_links),
        len(removed_scraped_files),
        error_count,
    )
    print(json.dumps(payload, indent=2))


if __name__ == "__main__":
    main()
