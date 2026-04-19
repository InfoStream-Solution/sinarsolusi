#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
APP_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"

IMAGE_NAME="${IMAGE_NAME:-ghcr.io/infostream-solution/sinarsolusi_dashboard}"
# IMAGE_TAG="${IMAGE_TAG:-$(date +%Y%m%d%H%M%S)}"
IMAGE_TAG="${IMAGE_TAG:-local}"

docker build \
  --file "${APP_DIR}/Dockerfile" \
  --tag "${IMAGE_NAME}:${IMAGE_TAG}" \
  "${APP_DIR}"
