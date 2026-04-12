#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

IMAGE_NAME="${IMAGE_NAME:-ghcr.io/infostream-solution/sinarsolusi_news_scraper}"
IMAGE_TAG="${IMAGE_TAG:-latest}"
ENV_FILE="${ENV_FILE:-/etc/news_scraper.env}"
LOG_FILE="${LOG_FILE:-/var/log/news-scraper-seed.log}"

exec >>"${LOG_FILE}" 2>&1

echo "[$(date -Is)] start"
cd "${SCRIPT_DIR}/../.."
IMAGE_NAME="${IMAGE_NAME}" IMAGE_TAG="${IMAGE_TAG}" ENV_FILE="${ENV_FILE}" \
  "${SCRIPT_DIR}/news_scraper.pull.sh"
IMAGE_NAME="${IMAGE_NAME}" IMAGE_TAG="${IMAGE_TAG}" ENV_FILE="${ENV_FILE}" \
  "${SCRIPT_DIR}/news_scraper.run.sh" seed kompas.com
echo "[$(date -Is)] exit=0"
