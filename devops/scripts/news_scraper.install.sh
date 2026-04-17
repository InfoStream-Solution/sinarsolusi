#!/usr/bin/env bash
set -euo pipefail

DEPLOY_USER="${DEPLOY_USER:-${SUDO_USER:-$(id -un)}}"
DATA_ROOT="${DATA_ROOT:-/var/lib/sinarsolusi}"

sudo mkdir -p "${DATA_ROOT}/seed" "${DATA_ROOT}/links" "${DATA_ROOT}/scraped" "${DATA_ROOT}/content" "${DATA_ROOT}/postgres"
sudo chown -R "${DEPLOY_USER}:${DEPLOY_USER}" "${DATA_ROOT}"

echo "Created ${DATA_ROOT} data directories and set ownership to ${DEPLOY_USER}:${DEPLOY_USER}"
