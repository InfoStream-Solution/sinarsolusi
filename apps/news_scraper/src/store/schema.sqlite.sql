CREATE TABLE IF NOT EXISTS link_meta (
    domain TEXT NOT NULL,
    url TEXT NOT NULL,
    discovered_at TEXT NOT NULL,
    scraped INTEGER NOT NULL DEFAULT 0,
    last_scraped_at TEXT,
    error_code TEXT,
    error_message TEXT,
    updated_at TEXT NOT NULL,
    PRIMARY KEY (domain, url)
);

CREATE INDEX IF NOT EXISTS idx_link_meta_domain_scraped
    ON link_meta(domain, scraped);

CREATE INDEX IF NOT EXISTS idx_link_meta_domain_updated_at
    ON link_meta(domain, updated_at);

CREATE TABLE IF NOT EXISTS news_article (
    domain TEXT NOT NULL,
    url TEXT NOT NULL,
    title TEXT NOT NULL,
    source_site TEXT NOT NULL,
    category TEXT,
    published_at TEXT,
    author TEXT,
    summary TEXT,
    content TEXT NOT NULL,
    word_count INTEGER NOT NULL,
    char_count INTEGER NOT NULL,
    scraped_at TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    PRIMARY KEY (domain, url)
);

CREATE INDEX IF NOT EXISTS idx_news_article_domain_scraped_at
    ON news_article(domain, scraped_at);

CREATE INDEX IF NOT EXISTS idx_news_article_domain_published_at
    ON news_article(domain, published_at);

CREATE TABLE IF NOT EXISTS news_article_attempt (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    domain TEXT NOT NULL,
    url TEXT NOT NULL,
    attempted_at TEXT NOT NULL,
    scraped INTEGER NOT NULL,
    error_code TEXT,
    error_message TEXT
);

CREATE INDEX IF NOT EXISTS idx_news_article_attempt_domain_url
    ON news_article_attempt(domain, url);

CREATE INDEX IF NOT EXISTS idx_news_article_attempt_domain_attempted_at
    ON news_article_attempt(domain, attempted_at);

CREATE INDEX IF NOT EXISTS idx_news_article_attempt_domain_scraped
    ON news_article_attempt(domain, scraped);

CREATE VIEW IF NOT EXISTS pending_links AS
SELECT *
FROM link_meta
WHERE scraped = 0;

CREATE VIEW IF NOT EXISTS scraped_links AS
SELECT *
FROM link_meta
WHERE scraped = 1;

CREATE VIEW IF NOT EXISTS failed_links AS
SELECT *
FROM link_meta
WHERE scraped = 0 AND error_code IS NOT NULL;
