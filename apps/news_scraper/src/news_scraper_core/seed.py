from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from news_scraper_core.config import get_settings
    from news_scraper_core.links import extract_domain_links
    from news_scraper_core.links import normalize_host
    from news_scraper_core.links import normalize_links
    from news_scraper_core.links import write_links
    from news_scraper_core.paths import links_jsonl_path
    from news_scraper_core.site_loader import load_site
    from news_scraper_core.utils import configure_logging
    from news_scraper_core.utils import get_logger
else:
    from .config import get_settings
    from .links import extract_domain_links
    from .links import normalize_host
    from .links import normalize_links
    from .links import write_links
    from .paths import links_jsonl_path
    from .site_loader import load_site
    from .utils import configure_logging
    from .utils import get_logger


def _load_additional_allowed_hosts(domain: str) -> set[str]:
    try:
        from news_admin.apps.sources.policy import get_additional_allowed_hosts
    except Exception:
        return set()
    return set(get_additional_allowed_hosts(domain))


def _register_discovered_hosts(domain: str, hosts: set[str]) -> dict[str, int]:
    try:
        from news_admin.apps.sources.policy import register_discovered_hosts
    except Exception:
        return {"created": 0, "skipped": len(hosts)}
    return register_discovered_hosts(domain, hosts)


def _seed_allowed_hosts(site) -> set[str]:
    return set(site.link_allowed_hosts) | _load_additional_allowed_hosts(site.domain)


def _link_host(url: str) -> str:
    from urllib.parse import urlparse

    return normalize_host(urlparse(url).netloc)


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
    args = parser.parse_args() if argv is None else parser.parse_args(argv[1:])

    settings = get_settings()

    configure_logging(debug=settings.scraper_debug)
    logger = get_logger("seed")
    site = load_site(args.domain, settings=settings)

    logger.info("seed_start domain=%r start_url=%r", site.domain, site.start_url)
    scrape_result = site.scrape()
    discovery_links = extract_domain_links(site.start_url, scrape_result.content)
    discovered_hosts = {_link_host(link.url) for link in discovery_links}
    host_update = _register_discovered_hosts(site.domain, discovered_hosts)
    allowed_hosts = _seed_allowed_hosts(site)

    links = [link for link in discovery_links if _link_host(link.url) in allowed_hosts]
    links = normalize_links(
        links,
        lambda url: (
            site.normalize_article_url(url)
            if site.is_article_url(url)
            else site.normalize_url(url)
        ),
    )
    links = [link for link in links if site.is_article_url(link.url)]
    links_path = links_jsonl_path(settings.links_dir, site.domain)
    write_links(links_path, links)
    logger.info(
        "seed_links_written domain=%r links_path=%r link_count=%d created_hosts=%d skipped_hosts=%d",
        site.domain,
        str(links_path),
        len(links),
        host_update["created"],
        host_update["skipped"],
    )

    seed_output_path = site.output_path
    removed_seed_file = False
    keep_seed = settings.keep_seed if args.keep_seed is None else args.keep_seed
    if not keep_seed and seed_output_path.exists():
        seed_output_path.unlink()
        removed_seed_file = True
        logger.info(
            "seed_cleanup domain=%r seed_output_path=%r",
            site.domain,
            str(seed_output_path),
        )

    payload = {
        "domain": site.domain,
        "start_url": site.start_url,
        "seed_output_path": str(seed_output_path),
        "keep_seed": keep_seed,
        "removed_seed_file": removed_seed_file,
        "links_output_path": str(links_path),
        "link_count": len(links),
        "created_hosts": host_update["created"],
        "skipped_hosts": host_update["skipped"],
    }
    logger.info(
        "seed_done domain=%r keep_seed=%r removed_seed_file=%r link_count=%d created_hosts=%d skipped_hosts=%d",
        site.domain,
        keep_seed,
        removed_seed_file,
        len(links),
        host_update["created"],
        host_update["skipped"],
    )
    logger.info(json.dumps(payload, indent=2))


if __name__ == "__main__":
    main()
