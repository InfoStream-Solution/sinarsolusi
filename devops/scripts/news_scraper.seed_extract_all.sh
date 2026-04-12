#!/usr/bin/env bash
set -euo pipefail

LOG_FILE="${LOG_FILE:-/var/log/news-scraper-seed-extract-all.log}"
LOCK_FILE="${LOCK_FILE:-/tmp/news-scraper-seed-extract-all.lock}"

exec >>"${LOG_FILE}" 2>&1

if ! /usr/bin/flock -n "${LOCK_FILE}" -c true; then
  echo "[$(date -Is)] skipped: previous run still active"
  exit 0
fi

echo "[$(date -Is)] seed_extract_all_start"

for domain in kompas.com detik.com beritasatu.com; do
  echo "[$(date -Is)] domain_start domain=${domain}"

  echo "[$(date -Is)] seed_start domain=${domain}"
  docker run --rm \
    -v /var/lib/sinarsolusi/data:/data \
    -v /etc/news_scraper.env:/app/.env:ro \
    ghcr.io/infostream-solution/sinarsolusi_news_scraper:latest \
    seed "$domain"
  echo "[$(date -Is)] seed_done domain=${domain} exit=0"

  echo "[$(date -Is)] extract_start domain=${domain}"
  docker run --rm \
    -v /var/lib/sinarsolusi/data:/data \
    -v /etc/news_scraper.env:/app/.env:ro \
    ghcr.io/infostream-solution/sinarsolusi_news_scraper:latest \
    extract-news "$domain"
  echo "[$(date -Is)] extract_done domain=${domain} exit=0"

  echo "[$(date -Is)] domain_done domain=${domain} exit=0"
done

echo "[$(date -Is)] seed_extract_all_done exit=0"
