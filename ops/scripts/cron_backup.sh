#!/usr/bin/env bash
set -Eeuo pipefail
umask 077

[[ $# -eq 1 && "$1" == /* ]] || {
  printf 'usage: %s /absolute/application/root\n' "$0" >&2
  exit 2
}

APP_ROOT=${1%/}
LOG_DIR="$APP_ROOT/shared/logs"
mkdir -p "$LOG_DIR"
LOG_FILE="$LOG_DIR/backup-$(date -u +%Y%m%d).log"

"$APP_ROOT/current/.venv/bin/python" "$APP_ROOT/current/scripts/backup.py" \
  --destination "$APP_ROOT/shared/backups" --retention-days 14 \
  >>"$LOG_FILE" 2>&1

find "$LOG_DIR" -type f -name 'backup-*.log' -mtime +30 -delete
