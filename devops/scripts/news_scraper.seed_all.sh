#!/usr/bin/env bash
set -euo pipefail

LOG_FILE="${LOG_FILE:-/var/log/news-scraper-seed-all.log}"

exec >>"${LOG_FILE}" 2>&1

echo "[$(date -Is)] seed_all_start"

for domain in kompas.com detik.com beritasatu.com; do
  echo "[$(date -Is)] domain_start domain=${domain}"
  docker run --rm \
    -v /var/lib/sinarsolusi/data:/data \
    -v /etc/news_scraper.env:/app/.env:ro \
    ghcr.io/infostream-solution/sinarsolusi_news_scraper:latest \
    seed "$domain"
  echo "[$(date -Is)] domain_done domain=${domain} exit=0"
done

echo "[$(date -Is)] seed_all_done exit=0"
