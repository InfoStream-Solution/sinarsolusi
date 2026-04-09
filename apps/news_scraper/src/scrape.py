from __future__ import annotations

import argparse
import json

from .config import get_settings
from .site_loader import load_site


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="scrape")
    parser.add_argument(
        "domain",
        help="Registered domain identifier, for example kompas.com.",
    )
    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    settings = get_settings()
    site = load_site(args.domain, settings=settings)
    result = site.scrape()

    payload = {
        "domain": site.domain,
        "start_url": site.start_url,
        "output_path": str(site.output_path),
        "content_length": len(result.content),
        "content_type": result.result.content_type,
    }
    print(json.dumps(payload, indent=2))


if __name__ == "__main__":
    main()
