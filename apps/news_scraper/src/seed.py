from __future__ import annotations

import argparse
import json

from .config import get_settings
from .links import extract_internal_links, write_links
from .paths import links_jsonl_path
from .site_loader import load_site


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


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    settings = get_settings()
    site = load_site(args.domain, settings=settings)
    scrape_result = site.scrape()

    links = extract_internal_links(
        site.start_url,
        scrape_result.content,
        allowed_hosts=site.link_allowed_hosts,
    )
    links_path = links_jsonl_path(settings.links_dir, site.domain)
    write_links(links_path, links)

    seed_output_path = site.output_path
    removed_seed_file = False
    keep_seed = settings.keep_seed if args.keep_seed is None else args.keep_seed
    if not keep_seed and seed_output_path.exists():
        seed_output_path.unlink()
        removed_seed_file = True

    payload = {
        "domain": site.domain,
        "start_url": site.start_url,
        "seed_output_path": str(seed_output_path),
        "keep_seed": keep_seed,
        "removed_seed_file": removed_seed_file,
        "links_output_path": str(links_path),
        "link_count": len(links),
    }
    print(json.dumps(payload, indent=2))


if __name__ == "__main__":
    main()
