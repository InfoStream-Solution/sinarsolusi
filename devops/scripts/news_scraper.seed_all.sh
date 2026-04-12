#!/usr/bin/env bash
set -euo pipefail

# Run this on server only not on local or dev machine.

for domain in kompas.com detik.com beritasatu.com; do
    echo "Running $domain"
    docker run --rm \
      -v /var/lib/sinarsolusi/data:/data \
      -v /etc/news_scraper.env:/app/.env:ro \
      ghcr.io/infostream-solution/sinarsolusi_news_scraper:latest \
      seed "$domain"
  done
