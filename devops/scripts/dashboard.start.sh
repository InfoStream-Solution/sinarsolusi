#!/usr/bin/env bash
set -euo pipefail

CONTAINER_NAME="${CONTAINER_NAME:-sinarsolusi-dashboard}"
IMAGE_NAME="${IMAGE_NAME:-ghcr.io/infostream-solution/sinarsolusi_dashboard}"
IMAGE_TAG="${IMAGE_TAG:-latest}"
HOST_PORT="${HOST_PORT:-3001}"
CONTAINER_PORT="${CONTAINER_PORT:-3000}"
ENV_FILE="${ENV_FILE:-/etc/sinarsolusi/dashboard.env}"

if [[ "${ENV_FILE}" == "/etc/sinarsolusi/dashboard.env" && ! -f "${ENV_FILE}" ]]; then
  printf 'missing required env file: %s\n' "${ENV_FILE}" >&2
  exit 1
fi

docker run -d \
  --name "${CONTAINER_NAME}" \
  --restart unless-stopped \
  --add-host=host.docker.internal:host-gateway \
  -p "${HOST_PORT}:${CONTAINER_PORT}" \
  --env-file "${ENV_FILE}" \
  "${IMAGE_NAME}:${IMAGE_TAG}"
