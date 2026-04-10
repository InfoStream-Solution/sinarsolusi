#!/usr/bin/env bash
set -euo pipefail

if [[ $# -ne 4 ]]; then
  cat <<'EOF'
usage: news_scraper.sync.sh <host> <user> <port> <target_dir>
EOF
  exit 1
fi

HOST="$1"
USER="$2"
PORT="$3"
TARGET_DIR="$4"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"

ssh -p "${PORT}" "${USER}@${HOST}" "mkdir -p '${TARGET_DIR}/deploy/runtime' '${TARGET_DIR}/ops/cron'"

rsync -avz -e "ssh -p ${PORT}" \
  "${REPO_ROOT}/deploy/runtime/" \
  "${USER}@${HOST}:${TARGET_DIR}/deploy/runtime/"

rsync -avz -e "ssh -p ${PORT}" \
  "${REPO_ROOT}/ops/cron/" \
  "${USER}@${HOST}:${TARGET_DIR}/ops/cron/"
