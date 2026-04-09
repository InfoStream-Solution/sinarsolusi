from __future__ import annotations

from pathlib import Path


def domain_dir(root_dir: Path, domain: str) -> Path:
    return root_dir / domain


def seed_html_path(scraped_dir: Path, domain: str) -> Path:
    return domain_dir(scraped_dir, domain) / "seed.html"


def links_json_path(scraped_dir: Path, domain: str) -> Path:
    return domain_dir(scraped_dir, domain) / "links.json"


def pages_dir(scraped_dir: Path, domain: str) -> Path:
    return domain_dir(scraped_dir, domain) / "pages"


def seed_file_path(seed_dir: Path, domain: str) -> Path:
    return seed_dir / f"{domain}.seed"


def links_jsonl_path(links_dir: Path, domain: str) -> Path:
    return links_dir / f"{domain}.jsonl"


def parsed_articles_dir(content_dir: Path, domain: str) -> Path:
    return content_dir / "news_article" / domain


def scraped_articles_dir(scraped_dir: Path, domain: str) -> Path:
    return scraped_dir / domain / "article_html"
