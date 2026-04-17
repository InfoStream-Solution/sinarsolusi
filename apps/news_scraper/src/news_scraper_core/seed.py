from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from news_scraper_core.config import get_settings
    from news_scraper_core.links import (
        extract_internal_links,
        normalize_links,
        write_links,
    )
    from news_scraper_core.paths import links_jsonl_path
    from news_scraper_core.site_loader import load_site
    from news_scraper_core.utils import configure_logging, get_logger
else:
    from .config import get_settings
    from .links import (
        extract_internal_links,
        normalize_links,
        write_links,
    )
    from .paths import links_jsonl_path
    from .site_loader import load_site
    from .utils import configure_logging, get_logger


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="seed")
    parser.add_argument(
        "domain",
        help="Registered domain identifier, for example kompas.com.",
    )
    parser.add_argument(
        "--keep-seed",
        action=argparse.BooleanOptionalAction,
        default=None,
        help="Keep the intermediate seed HTML file after link extraction.",
    )
    return parser


def main(argv: list[str] | None = None) -> None:
    parser = build_parser()
    args = parser.parse_args((argv or sys.argv)[1:])

    settings = get_settings()

    configure_logging(debug=settings.scraper_debug)
    logger = get_logger("seed")
    site = load_site(args.domain, settings=settings)

    logger.info("seed_start domain=%r start_url=%r", site.domain, site.start_url)
    scrape_result = site.scrape()

    links = extract_internal_links(
        site.start_url,
        scrape_result.content,
        allowed_hosts=site.link_allowed_hosts,
    )
    links = normalize_links(
        links,
        lambda url: site.normalize_article_url(url)
        if site.is_article_url(url)
        else site.normalize_url(url),
    )
    links = [link for link in links if site.is_article_url(link.url)]
    links_path = links_jsonl_path(settings.links_dir, site.domain)
    write_links(links_path, links)
    logger.info(
        "seed_links_written domain=%r links_path=%r link_count=%d",
        site.domain,
        str(links_path),
        len(links),
    )

    seed_output_path = site.output_path
    removed_seed_file = False
    keep_seed = settings.keep_seed if args.keep_seed is None else args.keep_seed
    if not keep_seed and seed_output_path.exists():
        seed_output_path.unlink()
        removed_seed_file = True
        logger.info("seed_cleanup domain=%r seed_output_path=%r", site.domain, str(seed_output_path))

    payload = {
        "domain": site.domain,
        "start_url": site.start_url,
        "seed_output_path": str(seed_output_path),
        "keep_seed": keep_seed,
        "removed_seed_file": removed_seed_file,
        "links_output_path": str(links_path),
        "link_count": len(links),
    }
    logger.info(
        "seed_done domain=%r keep_seed=%r removed_seed_file=%r link_count=%d",
        site.domain,
        keep_seed,
        removed_seed_file,
        len(links),
    )
    logger.info(json.dumps(payload, indent=2))


if __name__ == "__main__":
    main()
