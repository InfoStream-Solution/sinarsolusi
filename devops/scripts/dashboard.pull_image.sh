#!/usr/bin/env bash
set -euo pipefail

IMAGE_NAME="${IMAGE_NAME:-ghcr.io/infostream-solution/sinarsolusi_dashboard}"
IMAGE_TAG="${IMAGE_TAG:-latest}"

docker pull "${IMAGE_NAME}:${IMAGE_TAG}"
