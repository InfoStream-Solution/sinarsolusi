from __future__ import annotations

import argparse
import hashlib
import json
import re
import sqlite3
import unicodedata
from collections import Counter
from dataclasses import dataclass
from dataclasses import fields
from pathlib import Path

from .config import get_settings
from .models import ParsedContent
from .paths import grouped_articles_db_path, parsed_articles_dir
from .utils import configure_logging, get_logger

try:  # pragma: no cover - used after uv sync installs scikit-learn
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.metrics.pairwise import cosine_similarity
except ImportError:  # pragma: no cover - fallback before sync
    TfidfVectorizer = None  # type: ignore[assignment]
    cosine_similarity = None  # type: ignore[assignment]


STOPWORDS = {
    "a",
    "adalah",
    "agar",
    "akan",
    "atau",
    "bagi",
    "bahwa",
    "bisa",
    "dalam",
    "dengan",
    "dan",
    "dari",
    "di",
    "ini",
    "itu",
    "juga",
    "karena",
    "ke",
    "kini",
    "kami",
    "kamu",
    "lebih",
    "mereka",
    "oleh",
    "pada",
    "para",
    "saat",
    "sebagai",
    "setelah",
    "sudah",
    "untuk",
    "yang",
}

TOPIC_STOPWORDS = {
    "ke",
    "pb",
    "per",
    "the",
}

ROMAN_NUMERALS = {
    "i",
    "ii",
    "iii",
    "iv",
    "v",
    "vi",
    "vii",
    "viii",
    "ix",
    "x",
    "xi",
    "xii",
    "xiii",
    "xiv",
    "xv",
    "xvi",
    "xvii",
    "xviii",
    "xix",
    "xx",
}

TOKEN_RE = re.compile(r"[a-zA-Z][a-zA-Z0-9_+-]+")

SYNONYM_MAP = {
    "become": "increase",
    "becomes": "increase",
    "became": "increase",
    "becom": "increase",
    "grow": "increase",
    "grows": "increase",
    "grown": "increase",
    "increas": "increase",
    "naik": "increase",
    "kenaik": "increase",
    "hike": "increase",
    "hiked": "increase",
    "raising": "increase",
    "rais": "increase",
    "raised": "increase",
    "rise": "increase",
    "rising": "increase",
    "rose": "increase",
    "expensive": "increase",
    "expens": "increase",
    "mahal": "increase",
    "membengkak": "increase",
    "melonjak": "increase",
    "surge": "increase",
    "fuel": "fuel",
    "bahan": "fuel",
    "bakar": "fuel",
    "oil": "fuel",
    "minyak": "fuel",
    "petrol": "fuel",
    "gasoline": "fuel",
    "diesel": "fuel",
    "bbm": "fuel",
    "price": "price",
    "harga": "price",
}

TOPIC_WEIGHTS = {
    "fuel": 3,
    "increase": 3,
    "price": 2,
    "government": 1,
}

SIMILARITY_THRESHOLD = 0.20
MAX_PROFILE_TERMS = 36
TERM_REPEAT_CAP = 3
BODY_PARAGRAPH_LIMIT = 1
DOCUMENT_CHAR_LIMIT = 2500


@dataclass(frozen=True)
class ArticleFeatures:
    article_path: Path
    article: ParsedContent
    terms: list[str]
    ranked_terms: list[str]
    document: str


@dataclass(frozen=True)
class TopicGroup:
    group_id: str
    group_signature: str
    representative_texts: list[str]
    term_counts: dict[str, int]
    article_count: int
    first_published_at: str | None
    last_published_at: str | None


@dataclass(frozen=True)
class GroupMatch:
    group_id: str | None
    score: float


@dataclass(frozen=True)
class TopicNode:
    topic_id: str
    label: str
    topic_type: str
    support_count: int
    representative_terms_json: str
    created_at: str
    updated_at: str


def build_parser() -> argparse.ArgumentParser:
    """Build the CLI parser for incremental grouping."""

    parser = argparse.ArgumentParser(prog="group-news")
    mode_group = parser.add_mutually_exclusive_group()
    mode_group.add_argument(
        "--rebuild",
        action="store_true",
        help="Rebuild the global topic database from scratch before grouping.",
    )
    mode_group.add_argument(
        "--incremental",
        action="store_true",
        help="Preserve the existing topic database and append only new articles.",
    )
    parser.add_argument(
        "domain",
        help="Registered domain identifier, for example kompas.com.",
    )
    return parser


def normalize_token(token: str) -> str:
    lowered = token.lower().strip("._-+")
    lowered = SYNONYM_MAP.get(lowered, lowered)
    if lowered.endswith("ing") and len(lowered) > 5:
        lowered = lowered[:-3]
    if lowered.endswith("ed") and len(lowered) > 4:
        lowered = lowered[:-2]
    if lowered.endswith("s") and len(lowered) > 4:
        lowered = lowered[:-1]
    return SYNONYM_MAP.get(lowered, lowered)


def normalize_phrase(text: str) -> str:
    normalized = unicodedata.normalize("NFKC", text).lower().strip()
    normalized = re.sub(r"[^a-z0-9\s_-]+", " ", normalized)
    normalized = WHITESPACE_PATTERN.sub(" ", normalized).strip()
    return normalized


def extract_tokens(article: ParsedContent) -> list[str]:
    text = build_article_document(article)
    tokens: list[str] = []
    for raw_token in TOKEN_RE.findall(text.lower()):
        token = normalize_token(raw_token)
        if token in STOPWORDS or len(token) < 3:
            continue
        tokens.append(token)
    return tokens


WHITESPACE_PATTERN = re.compile(r"\s+")


def build_article_document(article: ParsedContent) -> str:
    parts = [article.title, article.title, article.summary or ""]
    content_paragraphs = [
        paragraph.strip()
        for paragraph in article.content.split("\n\n")
        if paragraph.strip()
    ]
    parts.extend(content_paragraphs[:BODY_PARAGRAPH_LIMIT])
    document = " ".join(part for part in parts if part)
    return document[:DOCUMENT_CHAR_LIMIT]


def article_phrases(article: ParsedContent) -> list[str]:
    title = normalize_phrase(article.title)
    phrases = [title]
    title_words = [word for word in title.split() if word]
    phrases.extend(
        " ".join(title_words[index : index + 2])
        for index in range(len(title_words) - 1)
    )
    first_paragraph = article.content.split("\n\n", 1)[0].strip()
    if first_paragraph:
        phrases.append(normalize_phrase(first_paragraph))
    return [phrase for phrase in phrases if phrase]


def canonical_topic_label(text: str) -> str:
    tokens = [
        token
        for token in normalize_phrase(text).split()
        if token and token not in TOPIC_STOPWORDS and token not in ROMAN_NUMERALS
    ]
    if not tokens:
        return ""
    if "munas" in tokens and "ipsi" in tokens:
        return "munas ipsi"
    if "prabowo" in tokens:
        return "prabowo"
    if "munas" in tokens:
        kept = ["munas", *[token for token in tokens if token != "munas"]]
        return " ".join(kept[:4])
    return " ".join(tokens[:4])


def extract_features(article_path: Path, article: ParsedContent) -> ArticleFeatures:
    tokens = extract_tokens(article)
    counts = Counter(tokens)
    ranked = sorted(
        counts.items(),
        key=lambda item: (-TOPIC_WEIGHTS.get(item[0], 0), -item[1], item[0]),
    )
    ranked_terms = [token for token, _ in ranked[:MAX_PROFILE_TERMS]]
    if not ranked_terms:
        ranked_terms = [article.source_site, article.title.lower()]
    document = build_article_document(article)
    return ArticleFeatures(
        article_path=article_path,
        article=article,
        terms=ranked_terms,
        ranked_terms=ranked_terms,
        document=document,
    )


def group_id_from_signature(signature: str) -> str:
    digest = hashlib.sha1(signature.encode("utf-8")).hexdigest()[:12]
    return f"group_{digest}"


def expand_term_counts(term_counts: dict[str, int]) -> str:
    expanded: list[str] = []
    for term, count in sorted(term_counts.items()):
        expanded.extend([term] * min(count, TERM_REPEAT_CAP))
    return " ".join(expanded)


def similarity_score(left_terms: list[str], right_terms: list[str]) -> float:
    if not left_terms or not right_terms:
        return 0.0
    overlap = set(left_terms) & set(right_terms)
    if not overlap:
        return 0.0
    return len(overlap) / min(len(set(left_terms)), len(set(right_terms)))


def read_articles(articles_dir: Path) -> list[tuple[Path, ParsedContent]]:
    articles: list[tuple[Path, ParsedContent]] = []
    parsed_content_fields = {field.name for field in fields(ParsedContent)}
    required_fields = {
        "content_type",
        "title",
        "url",
        "source_site",
        "category",
        "published_at",
        "author",
        "summary",
        "content",
        "word_count",
        "char_count",
        "scraped_at",
    }
    for article_path in sorted(articles_dir.glob("*.json")):
        if article_path.name.endswith(".posted.json"):
            continue
        payload = json.loads(article_path.read_text(encoding="utf-8"))
        if not required_fields.issubset(payload):
            continue
        filtered_payload = {
            key: value for key, value in payload.items() if key in parsed_content_fields
        }
        articles.append((article_path, ParsedContent(**filtered_payload)))
    return articles


def ensure_schema(connection: sqlite3.Connection) -> None:
    connection.executescript(
        """
        CREATE TABLE IF NOT EXISTS topic_groups (
            group_id TEXT PRIMARY KEY,
            group_signature TEXT NOT NULL,
            representative_text_json TEXT NOT NULL,
            representative_terms_json TEXT NOT NULL,
            term_counts_json TEXT NOT NULL,
            article_count INTEGER NOT NULL,
            first_published_at TEXT,
            last_published_at TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS topic_group_articles (
            article_path TEXT PRIMARY KEY,
            group_id TEXT NOT NULL,
            group_signature TEXT NOT NULL,
            title TEXT NOT NULL,
            source_site TEXT NOT NULL,
            url TEXT NOT NULL,
            published_at TEXT,
            score REAL NOT NULL,
            matched_terms TEXT NOT NULL,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            FOREIGN KEY (group_id) REFERENCES topic_groups(group_id)
        );

        CREATE TABLE IF NOT EXISTS topic_group_events (
            event_id INTEGER PRIMARY KEY AUTOINCREMENT,
            group_id TEXT NOT NULL,
            article_path TEXT NOT NULL,
            source_site TEXT NOT NULL,
            url TEXT NOT NULL,
            published_at TEXT,
            created_at TEXT NOT NULL,
            FOREIGN KEY (group_id) REFERENCES topic_groups(group_id),
            FOREIGN KEY (article_path) REFERENCES topic_group_articles(article_path)
        );

        CREATE TABLE IF NOT EXISTS topic_nodes (
            topic_id TEXT PRIMARY KEY,
            label TEXT NOT NULL,
            topic_type TEXT NOT NULL,
            support_count INTEGER NOT NULL,
            representative_terms_json TEXT NOT NULL,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS article_topic_memberships (
            article_path TEXT NOT NULL,
            topic_id TEXT NOT NULL,
            topic_score REAL NOT NULL,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            PRIMARY KEY (article_path, topic_id),
            FOREIGN KEY (topic_id) REFERENCES topic_nodes(topic_id)
        );
        """
    )
    columns = {
        row[1] for row in connection.execute("PRAGMA table_info(topic_groups)")
    }
    if "representative_text_json" not in columns:
        connection.execute(
            """
            ALTER TABLE topic_groups
            ADD COLUMN representative_text_json TEXT NOT NULL DEFAULT '[]'
            """
        )


def topic_id_from_label(label: str) -> str:
    return f"topic_{hashlib.sha1(label.encode('utf-8')).hexdigest()[:12]}"


def build_topic_candidates(feature: ArticleFeatures) -> list[tuple[str, str, float]]:
    candidates: list[tuple[str, str, float]] = []
    phrase_scores = Counter()
    for phrase in article_phrases(feature.article):
        label = canonical_topic_label(phrase)
        if label:
            phrase_scores[label] += 1
    for phrase, score in phrase_scores.items():
        label = phrase[:120]
        topic_type = "event" if len(label.split()) >= 2 else "entity"
        candidates.append((label, topic_type, float(score)))

    for term in feature.ranked_terms[:6]:
        candidates.append((term, "entity", 1.0))

    deduped: dict[str, tuple[str, str, float]] = {}
    for label, topic_type, score in candidates:
        topic_id = topic_id_from_label(label)
        current = deduped.get(topic_id)
        if current is None or score > current[2]:
            deduped[topic_id] = (label, topic_type, score)
    return sorted(deduped.values(), key=lambda item: (-item[2], item[0]))


def upsert_topic_node(connection: sqlite3.Connection, label: str, topic_type: str, terms: list[str]) -> str:
    topic_id = topic_id_from_label(label)
    existing = connection.execute(
        "SELECT support_count, representative_terms_json FROM topic_nodes WHERE topic_id = ?",
        (topic_id,),
    ).fetchone()
    if existing is None:
        connection.execute(
            """
            INSERT INTO topic_nodes (
                topic_id,
                label,
                topic_type,
                support_count,
                representative_terms_json,
                created_at,
                updated_at
            ) VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
            """,
            (
                topic_id,
                label,
                topic_type,
                1,
                json.dumps(terms, ensure_ascii=False),
            ),
        )
        return topic_id

    support_count = int(existing[0]) + 1
    current_terms = json.loads(existing[1])
    merged_terms = list(dict.fromkeys((current_terms + terms)[:12]))
    existing_label = connection.execute(
        "SELECT label, topic_type FROM topic_nodes WHERE topic_id = ?",
        (topic_id,),
    ).fetchone()
    if existing_label is not None:
        label = existing_label[0]
        topic_type = existing_label[1]
    connection.execute(
        """
        UPDATE topic_nodes
        SET label = ?, topic_type = ?, support_count = ?, representative_terms_json = ?, updated_at = CURRENT_TIMESTAMP
        WHERE topic_id = ?
        """,
        (
            label,
            topic_type,
            support_count,
            json.dumps(merged_terms, ensure_ascii=False),
            topic_id,
        ),
    )
    return topic_id


def write_topic_memberships(connection: sqlite3.Connection, feature: ArticleFeatures) -> None:
    for label, topic_type, score in build_topic_candidates(feature):
        if score <= 0:
            continue
        topic_id = upsert_topic_node(connection, label, topic_type, feature.ranked_terms[:8])
        connection.execute(
            """
            INSERT INTO article_topic_memberships (
                article_path,
                topic_id,
                topic_score,
                created_at,
                updated_at
            ) VALUES (?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
            ON CONFLICT(article_path, topic_id) DO UPDATE SET
                topic_score=excluded.topic_score,
                updated_at=CURRENT_TIMESTAMP
            """,
            (str(feature.article_path), topic_id, score),
        )


def read_existing_groups(connection: sqlite3.Connection) -> dict[str, TopicGroup]:
    rows = connection.execute(
        """
        SELECT group_id, group_signature, representative_text_json,
               term_counts_json, article_count, first_published_at, last_published_at
        FROM topic_groups
        """
    ).fetchall()
    groups: dict[str, TopicGroup] = {}
    for row in rows:
        groups[row[0]] = TopicGroup(
            group_id=row[0],
            group_signature=row[1],
            representative_texts=json.loads(row[2]),
            term_counts=json.loads(row[3]),
            article_count=int(row[4]),
            first_published_at=row[5],
            last_published_at=row[6],
        )
    return groups


def read_existing_article_paths(connection: sqlite3.Connection) -> set[str]:
    rows = connection.execute(
        "SELECT article_path FROM topic_group_articles"
    ).fetchall()
    return {row[0] for row in rows}


def build_group_signature(terms: list[str]) -> str:
    return "|".join(terms[:12])


def create_group_state(feature: ArticleFeatures) -> TopicGroup:
    counts = Counter(feature.ranked_terms)
    representative_terms = extract_representative_terms(dict(counts))
    return TopicGroup(
        group_id=group_id_from_signature(
            build_group_signature(representative_terms)
            + "|"
            + feature.article.url
        ),
        group_signature=build_group_signature(representative_terms),
        representative_texts=[feature.document],
        term_counts=dict(counts),
        article_count=1,
        first_published_at=feature.article.published_at,
        last_published_at=feature.article.published_at,
    )


def extract_representative_terms(term_counts: dict[str, int]) -> list[str]:
    ranked = sorted(
        term_counts.items(),
        key=lambda item: (-TOPIC_WEIGHTS.get(item[0], 0), -item[1], item[0]),
    )
    return [token for token, _ in ranked[:MAX_PROFILE_TERMS]]


def update_group_state(group: TopicGroup, feature: ArticleFeatures) -> TopicGroup:
    counts = Counter(group.term_counts)
    counts.update(feature.ranked_terms)
    representative_terms = extract_representative_terms(dict(counts))
    first_published_at = group.first_published_at
    last_published_at = group.last_published_at
    published_at = feature.article.published_at
    if first_published_at is None or (
        published_at is not None and published_at < first_published_at
    ):
        first_published_at = published_at
    if last_published_at is None or (
        published_at is not None and published_at > last_published_at
    ):
        last_published_at = published_at
    return TopicGroup(
        group_id=group.group_id,
        group_signature=build_group_signature(representative_terms),
        representative_texts=(group.representative_texts + [feature.document])[-6:],
        term_counts=dict(counts),
        article_count=group.article_count + 1,
        first_published_at=first_published_at,
        last_published_at=last_published_at,
    )


def group_document(group: TopicGroup) -> str:
    return " ".join(group.representative_texts + [expand_term_counts(group.term_counts)])


def choose_group(feature: ArticleFeatures, groups: list[TopicGroup]) -> GroupMatch:
    if not groups:
        return GroupMatch(group_id=None, score=0.0)

    if TfidfVectorizer is not None and cosine_similarity is not None:
        documents = [feature.document, *[group_document(group) for group in groups]]
        vectorizer = TfidfVectorizer(analyzer="char_wb", ngram_range=(4, 6))
        matrix = vectorizer.fit_transform(documents)
        similarities = cosine_similarity(matrix[:1], matrix[1:]).ravel()
        best_index = int(similarities.argmax())
        best_score = float(similarities[best_index])
        if best_score < SIMILARITY_THRESHOLD:
            return GroupMatch(group_id=None, score=best_score)
        return GroupMatch(group_id=groups[best_index].group_id, score=best_score)

    best_group_id = None
    best_score = 0.0
    for group in groups:
        score = similarity_score(feature.terms, list(group.term_counts))
        if score > best_score:
            best_group_id = group.group_id
            best_score = score
    if best_score < SIMILARITY_THRESHOLD:
        return GroupMatch(group_id=None, score=best_score)
    if best_group_id is None:
        return GroupMatch(group_id=None, score=best_score)
    return GroupMatch(group_id=best_group_id, score=best_score)


def write_group_state(connection: sqlite3.Connection, group: TopicGroup) -> None:
    representative_terms = extract_representative_terms(group.term_counts)
    connection.execute(
        """
        INSERT INTO topic_groups (
            group_id,
            group_signature,
            representative_text_json,
            representative_terms_json,
            term_counts_json,
            article_count,
            first_published_at,
            last_published_at,
            created_at,
            updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
        ON CONFLICT(group_id) DO UPDATE SET
            group_signature=excluded.group_signature,
            representative_text_json=excluded.representative_text_json,
            representative_terms_json=excluded.representative_terms_json,
            term_counts_json=excluded.term_counts_json,
            article_count=excluded.article_count,
            first_published_at=excluded.first_published_at,
            last_published_at=excluded.last_published_at,
            updated_at=CURRENT_TIMESTAMP
        """,
        (
            group.group_id,
            group.group_signature,
            json.dumps(group.representative_texts, ensure_ascii=False),
            json.dumps(representative_terms, ensure_ascii=False),
            json.dumps(group.term_counts, ensure_ascii=False),
            group.article_count,
            group.first_published_at,
            group.last_published_at,
        ),
    )


def write_article_membership(
    connection: sqlite3.Connection,
    feature: ArticleFeatures,
    group: TopicGroup,
    score: float,
) -> None:
    matched_terms = sorted(set(feature.ranked_terms) & set(group.term_counts))
    if not matched_terms:
        matched_terms = feature.ranked_terms[:3]
    connection.execute(
        """
        INSERT INTO topic_group_articles (
            article_path,
            group_id,
            group_signature,
            title,
            source_site,
            url,
            published_at,
            score,
            matched_terms,
            created_at,
            updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
        ON CONFLICT(article_path) DO UPDATE SET
            group_id=excluded.group_id,
            group_signature=excluded.group_signature,
            title=excluded.title,
            source_site=excluded.source_site,
            url=excluded.url,
            published_at=excluded.published_at,
            score=excluded.score,
            matched_terms=excluded.matched_terms,
            updated_at=CURRENT_TIMESTAMP
        """,
        (
            str(feature.article_path),
            group.group_id,
            group.group_signature,
            feature.article.title,
            feature.article.source_site,
            feature.article.url,
            feature.article.published_at,
            score,
            ",".join(matched_terms),
        ),
    )
    connection.execute(
        """
        INSERT INTO topic_group_events (
            group_id,
            article_path,
            source_site,
            url,
            published_at,
            created_at
        ) VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
        """,
        (
            group.group_id,
            str(feature.article_path),
            feature.article.source_site,
            feature.article.url,
            feature.article.published_at,
        ),
    )


def ingest_articles(
    connection: sqlite3.Connection,
    articles: list[tuple[Path, ParsedContent]],
) -> tuple[int, int]:
    existing_groups = read_existing_groups(connection)
    existing_article_paths = read_existing_article_paths(connection)
    new_group_count = 0
    matched_count = 0

    for article_path, article in articles:
        article_path_str = str(article_path)
        if article_path_str in existing_article_paths:
            continue

        feature = extract_features(article_path, article)
        group_list = list(existing_groups.values())
        match = choose_group(feature, group_list)

        if match.group_id is None or match.score < SIMILARITY_THRESHOLD:
            group = create_group_state(feature)
            new_group_count += 1
            score = 1.0
        else:
            group = update_group_state(existing_groups[match.group_id], feature)
            matched_count += 1
            score = match.score

        existing_groups[group.group_id] = group
        write_group_state(connection, group)
        write_article_membership(connection, feature, group, score)
        write_topic_memberships(connection, feature)
        existing_article_paths.add(article_path_str)

    return new_group_count, matched_count


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    settings = get_settings()
    configure_logging(debug=settings.scraper_debug)
    logger = get_logger("group-news")
    articles_dir = parsed_articles_dir(settings.content_dir, args.domain)
    grouped_db_path = grouped_articles_db_path(settings.content_dir)
    grouped_db_path.parent.mkdir(parents=True, exist_ok=True)
    rebuild = bool(getattr(args, "rebuild", False))
    incremental = bool(getattr(args, "incremental", False))
    if not rebuild and not incremental:
        rebuild = True
    if rebuild and grouped_db_path.exists():
        grouped_db_path.unlink()
        logger.info("group_news_rebuild_reset grouped_db_path=%r", str(grouped_db_path))

    articles = read_articles(articles_dir)
    connection = sqlite3.connect(grouped_db_path)
    try:
        ensure_schema(connection)
        new_group_count, matched_count = ingest_articles(connection, articles)
        connection.commit()
    finally:
        connection.close()

    logger.info(
        "group_news_done domain=%r article_count=%d new_group_count=%d matched_count=%d grouped_db_path=%r",
        args.domain,
        len(articles),
        new_group_count,
        matched_count,
        str(grouped_db_path),
    )
    print(
        json.dumps(
            {
                "domain": args.domain,
                "articles_dir": str(articles_dir),
                "grouped_db_path": str(grouped_db_path),
                "article_count": len(articles),
                "new_group_count": new_group_count,
                "matched_count": matched_count,
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
