#!/usr/bin/env bash
set -euo pipefail

CONTAINER_NAME="${CONTAINER_NAME:-sinarsolusi-dashboard}"

docker logs -f "${CONTAINER_NAME}"
