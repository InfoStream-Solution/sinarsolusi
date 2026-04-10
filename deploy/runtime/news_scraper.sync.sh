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
SSH_KEY="${SSH_KEY:-$HOME/.ssh/news_scraper_ci_key}"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"

ssh -i "${SSH_KEY}" -p "${PORT}" "${USER}@${HOST}" "mkdir -p '${TARGET_DIR}/deploy/runtime' '${TARGET_DIR}/ops/cron' '${TARGET_DIR}/ops/bootstrap' '${TARGET_DIR}/apps/news_scraper'"

RSYNC_SSH="ssh -i ${SSH_KEY} -p ${PORT}"

rsync -avz -e "${RSYNC_SSH}" \
  "${REPO_ROOT}/deploy/runtime/" \
  "${USER}@${HOST}:${TARGET_DIR}/deploy/runtime/"

rsync -avz -e "${RSYNC_SSH}" \
  "${REPO_ROOT}/ops/cron/" \
  "${USER}@${HOST}:${TARGET_DIR}/ops/cron/"

rsync -avz -e "${RSYNC_SSH}" \
  "${REPO_ROOT}/ops/bootstrap/" \
  "${USER}@${HOST}:${TARGET_DIR}/ops/bootstrap/"

rsync -avz -e "${RSYNC_SSH}" \
  "${REPO_ROOT}/apps/news_scraper/compose.yaml" \
  "${USER}@${HOST}:${TARGET_DIR}/apps/news_scraper/compose.yaml"
