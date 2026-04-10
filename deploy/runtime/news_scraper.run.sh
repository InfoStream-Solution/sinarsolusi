#!/usr/bin/env bash
set -euo pipefail

IMAGE_NAME="${IMAGE_NAME:-ghcr.io/infostream-solution/sinarsolusi_news_scraper}"
IMAGE_TAG="${IMAGE_TAG:-latest}"
ENV_FILE="${ENV_FILE:-/etc/news_scraper.env}"

docker run --rm \
  --env-file "${ENV_FILE}" \
  "${IMAGE_NAME}:${IMAGE_TAG}" \
  uv run seed kompas.com
