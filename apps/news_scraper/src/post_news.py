from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass
from datetime import UTC, datetime, timedelta, timezone
from pathlib import Path
from urllib import request

from .config import get_settings
from .models import ParsedContent
from .paths import error_log_path, parsed_articles_dir
from .utils import configure_logging, get_logger


@dataclass(frozen=True)
class PostedRecord:
    """Record of a successfully posted article."""

    url: str
    posted_at: str
    response_status: int


_MONTHS = {
    "januari": 1,
    "februari": 2,
    "maret": 3,
    "april": 4,
    "mei": 5,
    "juni": 6,
    "juli": 7,
    "agustus": 8,
    "september": 9,
    "oktober": 10,
    "november": 11,
    "desember": 12,
}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="post-news")
    parser.add_argument(
        "domain",
        help="Registered domain identifier, for example kompas.com.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=0,
        help="Maximum number of parsed articles to post. 0 means no limit.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Validate and print the payloads without posting them.",
    )
    return parser


def now_iso() -> str:
    return datetime.now(UTC).isoformat()


def normalize_published_at(published_at: str | None) -> str | None:
    if not published_at:
        return None

    raw_value = published_at.strip()
    if not raw_value:
        return None

    try:
        parsed = datetime.fromisoformat(raw_value)
    except ValueError:
        parsed = None

    if parsed is not None:
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed.isoformat()

    try:
        date_part, time_part = raw_value.rsplit(",", 1)
        day_text, month_text, year_text = date_part.strip().split()
        clock_text = time_part.strip().split()[0]
        hour_text, minute_text = clock_text.split(":", 1)
        month = _MONTHS[month_text.lower()]
        parsed = datetime(
            int(year_text),
            month,
            int(day_text),
            int(hour_text),
            int(minute_text),
            tzinfo=timezone(timedelta(hours=7)),
        )
    except (KeyError, ValueError):
        return raw_value

    return parsed.isoformat()


def parsed_article_path(content_dir: Path, domain: str, slug: str) -> Path:
    return parsed_articles_dir(content_dir, domain) / f"{slug}.json"


def title_slug_from_path(path: Path) -> str:
    return path.stem


def load_parsed_article(path: Path) -> ParsedContent:
    payload = json.loads(path.read_text(encoding="utf-8"))
    return ParsedContent(**payload)


def build_request_body(article: ParsedContent) -> dict[str, object]:
    body: dict[str, object] = {
        "title": article.title,
        "content": article.content,
    }
    normalized_published_at = normalize_published_at(article.published_at)
    if normalized_published_at:
        body["published_at"] = normalized_published_at
    return body


def post_article(
    *,
    base_url: str,
    token: str,
    article: ParsedContent,
) -> tuple[int, str]:
    body = json.dumps(build_request_body(article)).encode("utf-8")
    api_request = request.Request(
        f"{base_url}/api/news/",
        data=body,
        method="POST",
        headers={
            "Authorization": f"Token {token}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        },
    )
    with request.urlopen(api_request, timeout=30) as response:
        response_body = response.read().decode("utf-8")
        return response.status, response_body


def append_error_record(path: Path, record: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, ensure_ascii=False) + "\n")


def save_posted_record(
    path: Path,
    *,
    url: str,
    response_status: int,
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    record = PostedRecord(url=url, posted_at=now_iso(), response_status=response_status)
    path.write_text(json.dumps(asdict(record), indent=2, ensure_ascii=False), encoding="utf-8")


def log_dry_run(
    *,
    logger,
    article_path: Path,
    article: ParsedContent,
    payload: dict[str, object],
) -> None:
    logger.info(
        "post_news_dry_run article_path=%r title=%r payload=%s",
        str(article_path),
        article.title,
        json.dumps(payload, ensure_ascii=False),
    )


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    settings = get_settings()
    configure_logging(debug=settings.scraper_debug)
    logger = get_logger("post-news")

    if not args.dry_run and not settings.kbt_api_token:
        raise SystemExit("KBT_API_TOKEN is required for post-news")

    articles_dir = parsed_articles_dir(settings.content_dir, args.domain)
    article_paths = sorted(articles_dir.glob("*.json"))
    if args.limit > 0:
        article_paths = article_paths[: args.limit]

    logger.info(
        "post_news_start domain=%r articles_dir=%r article_count=%d",
        args.domain,
        str(articles_dir),
        len(article_paths),
    )

    error_path = error_log_path(settings.content_dir, args.domain, "post-news")
    posted_count = 0
    failed_count = 0
    posted_files: list[str] = []

    for article_path in article_paths:
        article = load_parsed_article(article_path)
        posted_marker = article_path.with_suffix(".posted.json")
        if posted_marker.exists():
            posted_files.append(str(posted_marker))
            continue

        payload_body = build_request_body(article)
        if args.dry_run:
            log_dry_run(
                logger=logger,
                article_path=article_path,
                article=article,
                payload=payload_body,
            )
            continue

        try:
            response_status, response_body = post_article(
                base_url=settings.kbt_api_base_url,
                token=settings.kbt_api_token,
                article=article,
            )
            posted_count += 1
            save_posted_record(
                posted_marker,
                url=article.url,
                response_status=response_status,
            )
            posted_files.append(str(posted_marker))
            logger.info(
                "post_news_done article_path=%r response_status=%d",
                str(article_path),
                response_status,
            )
            _ = response_body
        except Exception as exc:
            failed_count += 1
            logger.exception("post_news_failed article_path=%r", str(article_path))
            append_error_record(
                error_path,
                {
                    "occurred_at": now_iso(),
                    "domain": args.domain,
                    "command": "post-news",
                    "article_path": str(article_path),
                    "article_url": article.url,
                    "error_type": type(exc).__name__,
                    "error_message": str(exc),
                },
            )

    payload = {
        "domain": args.domain,
        "articles_dir": str(articles_dir),
        "article_count": len(article_paths),
        "posted_count": posted_count,
        "failed_count": failed_count,
        "posted_files": posted_files,
        "error_log_path": str(error_path),
    }
    logger.info(
        "post_news_done domain=%r posted_count=%d failed_count=%d",
        args.domain,
        posted_count,
        failed_count,
    )
    print(json.dumps(payload, indent=2))


if __name__ == "__main__":
    main()
