#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
COMPOSE_FILE="${REPO_ROOT}/devops/runtime/news_scraper.compose.yaml"

IMAGE_TAG="${IMAGE_TAG:-latest}"
ENV_FILE="${ENV_FILE:-/etc/news_scraper.env}"

if [[ "${ENV_FILE}" == "/etc/news_scraper.env" && ! -f "${ENV_FILE}" ]]; then
  printf "missing required env file: %s\n" "${ENV_FILE}" >&2
  exit 1
fi

IMAGE_TAG="${IMAGE_TAG}" ENV_FILE="${ENV_FILE}" \
  docker compose -f "${COMPOSE_FILE}" run --rm web \
  python -m news_admin.manage migrate
