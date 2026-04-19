#!/usr/bin/env bash
set -euo pipefail

CONTAINER_NAME="${CONTAINER_NAME:-sinarsolusi-dashboard}"

docker stop "${CONTAINER_NAME}"
