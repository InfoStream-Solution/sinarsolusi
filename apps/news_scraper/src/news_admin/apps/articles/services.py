from __future__ import annotations

from urllib.parse import urlparse

from django.utils import timezone
from django.utils.dateparse import parse_datetime

from news_scraper_core.config import get_settings
from news_scraper_core.post_news import normalize_published_at
from news_scraper_core.site_loader import load_site

from .models import Article


def _to_datetime(raw_value: str | None):
    if not raw_value:
        return None
    parsed = parse_datetime(raw_value)
    if parsed is not None:
        return parsed
    normalized = normalize_published_at(raw_value)
    if normalized:
        parsed = parse_datetime(normalized)
        if parsed is not None:
            return parsed
    return None


def _merge_timestamp(existing, new_value):
    return new_value if new_value is not None else existing


def _domain_from_url(url: str) -> str:
    host = urlparse(url).netloc.lower()
    if host.startswith("www."):
        host = host[4:]
    return host


def _resolve_site_domain(article: Article) -> str:
    if article.source_site:
        return article.source_site
    return _domain_from_url(article.url)


def _save_article_timestamp_fields(article: Article, *, published_at, scraped_at) -> None:
    update_fields = ["url", "title", "source_site", "content", "updated_at"]
    if published_at is not None:
        update_fields.append("published_at")
        article.published_at = published_at
    if scraped_at is not None:
        update_fields.append("scraped_at")
        article.scraped_at = scraped_at
    article.save(update_fields=update_fields)


def import_articles_for_domain(domain: str, *, content_dir=None) -> dict[str, int]:
    from pathlib import Path
    import json

    from .models import ArticleImportRun

    if content_dir is not None:
        root_dir = Path(content_dir)
    else:
        root_dir = get_settings().content_dir
    articles_dir = root_dir / "news_article" / domain
    json_paths = sorted(articles_dir.glob("*.json"))

    run = ArticleImportRun.objects.create(
        domain=domain,
        content_dir=str(root_dir),
        status=ArticleImportRun.Status.RUNNING,
        started_at=timezone.now(),
        file_paths=[str(path) for path in json_paths],
    )

    created = 0
    updated = 0
    skipped = 0

    try:
        for json_path in json_paths:
            payload = json.loads(json_path.read_text(encoding="utf-8"))
            url = payload["url"]
            existing = Article.objects.filter(url=url).first()
            published_at = _to_datetime(payload.get("published_at"))
            scraped_at = _to_datetime(payload.get("scraped_at"))
            if existing is not None:
                published_at = _merge_timestamp(existing.published_at, published_at)
                scraped_at = _merge_timestamp(existing.scraped_at, scraped_at)
            defaults = {
                "title": payload.get("title", ""),
                "source_site": payload.get("source_site", domain),
                "content": payload.get("content", ""),
                "published_at": published_at,
                "scraped_at": scraped_at,
            }
            _, was_created = Article.objects.update_or_create(url=url, defaults=defaults)
            if was_created:
                created += 1
            else:
                updated += 1
            if not payload.get("content"):
                skipped += 1
    except Exception as exc:
        run.status = ArticleImportRun.Status.FAILED
        run.error_message = f"{type(exc).__name__}: {exc}"
        run.scanned_files = len(json_paths)
        run.created_count = created
        run.updated_count = updated
        run.skipped_count = skipped
        run.finished_at = timezone.now()
        run.save(
            update_fields=[
                "status",
                "error_message",
                "scanned_files",
                "created_count",
                "updated_count",
                "skipped_count",
                "finished_at",
            ]
        )
        raise

    run.status = ArticleImportRun.Status.SUCCEEDED
    run.scanned_files = len(json_paths)
    run.created_count = created
    run.updated_count = updated
    run.skipped_count = skipped
    run.finished_at = timezone.now()
    run.save(
        update_fields=[
            "status",
            "scanned_files",
            "created_count",
            "updated_count",
            "skipped_count",
            "finished_at",
        ]
    )

    return {
        "domain": domain,
        "scanned_files": len(json_paths),
        "created": created,
        "updated": updated,
        "skipped": skipped,
        "import_run_id": run.id,
    }


def refresh_article_from_source(article: Article) -> dict[str, object]:
    settings_obj = get_settings()
    site_domain = _resolve_site_domain(article)
    site = load_site(site_domain, settings=settings_obj)
    normalized_url = site.normalize_article_url(article.url)
    if not site.is_article_url(normalized_url):
        raise ValueError(f"{normalized_url!r} is not a valid article URL for {site.domain}")

    site.scrape_article(normalized_url)
    html_path = site.scraped_article_output_path(normalized_url)
    html = html_path.read_text(encoding="utf-8")
    parsed = site.parse_article(html, normalized_url)
    parsed_path = site.save_parsed_article(parsed, normalized_url)
    markdown_path = site.article_markdown_output_path(normalized_url)

    article.url = normalized_url
    article.title = parsed.title
    article.source_site = parsed.source_site
    article.content = parsed.content
    published_at = _to_datetime(parsed.published_at)
    scraped_at = _to_datetime(parsed.scraped_at)
    _save_article_timestamp_fields(article, published_at=published_at, scraped_at=scraped_at)

    if html_path.exists():
        html_path.unlink()

    return {
        "article_id": article.id,
        "url": article.url,
        "json_path": str(parsed_path),
        "markdown_path": str(markdown_path),
    }
