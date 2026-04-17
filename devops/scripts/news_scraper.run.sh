#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
COMPOSE_FILE="${REPO_ROOT}/devops/runtime/news_scraper.compose.yaml"

IMAGE_NAME="${IMAGE_NAME:-ghcr.io/infostream-solution/sinarsolusi_news_scraper}"
IMAGE_TAG="${IMAGE_TAG:-latest}"
ENV_FILE="${ENV_FILE:-/etc/news_scraper.env}"

if [[ "${ENV_FILE}" == "/etc/news_scraper.env" && ! -f "${ENV_FILE}" ]]; then
  printf 'missing required env file: %s\n' "${ENV_FILE}" >&2
  exit 1
fi

if [[ $# -eq 0 ]]; then
  set -- seed kompas.com
fi

IMAGE_NAME="${IMAGE_NAME}" IMAGE_TAG="${IMAGE_TAG}" ENV_FILE="${ENV_FILE}" SCRAPER_DEBUG="${SCRAPER_DEBUG:-0}" KEEP_SEED="${KEEP_SEED:-0}" KEEP_SCRAPED="${KEEP_SCRAPED:-0}" \
  docker compose --profile job -f "${COMPOSE_FILE}" run --rm \
  news-scraper \
  "$@"
