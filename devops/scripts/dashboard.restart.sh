#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

bash "${SCRIPT_DIR}/dashboard.stop.sh" >/dev/null 2>&1 || true
bash "${SCRIPT_DIR}/dashboard.start.sh"
