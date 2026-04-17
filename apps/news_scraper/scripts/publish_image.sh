#!/usr/bin/env bash
set -euo pipefail

IMAGE_NAME="${IMAGE_NAME:-ghcr.io/infostream-solution/sinarsolusi_news_scraper}"
SOURCE_TAG="${SOURCE_TAG:-local}"
PUBLISH_TAG="${PUBLISH_TAG:-latest}"

docker tag "${IMAGE_NAME}:${SOURCE_TAG}" "${IMAGE_NAME}:${PUBLISH_TAG}"
docker push "${IMAGE_NAME}:${PUBLISH_TAG}"
