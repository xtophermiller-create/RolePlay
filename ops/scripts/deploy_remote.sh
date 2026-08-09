#!/usr/bin/env bash
set -Eeuo pipefail
umask 077

die() {
  printf 'deploy error: %s\n' "$*" >&2
  exit 1
}

[[ $# -eq 7 ]] ||
  die "expected: APP_ROOT RELEASE_ID ARCHIVE SHA256 PYTHON PUBLIC_BASE_URL PASSENGER_RESTART_FILE"
APP_ROOT=$1
RELEASE_ID=$2
ARCHIVE=$3
EXPECTED_SHA=$4
PYTHON=$5
PUBLIC_BASE_URL=${6%/}
PASSENGER_RESTART_FILE=$7

[[ "$APP_ROOT" == /* && "$APP_ROOT" != *".."* && "$APP_ROOT" != *" "* ]] ||
  die "APP_ROOT must be an absolute path without spaces or '..'"
[[ "$RELEASE_ID" =~ ^[0-9TZ-]+[a-f0-9]{8}$ ]] || die "invalid release id"
[[ "$EXPECTED_SHA" =~ ^[a-f0-9]{64}$ ]] || die "invalid SHA-256"
[[ "$PUBLIC_BASE_URL" =~ ^https://[A-Za-z0-9.-]+(:[0-9]+)?$ ]] ||
  die "PUBLIC_BASE_URL must be an HTTPS origin without a path"
[[ "$PASSENGER_RESTART_FILE" == /* && "$PASSENGER_RESTART_FILE" != *".."* &&
  "$PASSENGER_RESTART_FILE" != *" "* ]] ||
  die "PASSENGER_RESTART_FILE must be an absolute path without spaces or '..'"

RELEASES="$APP_ROOT/releases"
SHARED="$APP_ROOT/shared"
CURRENT="$APP_ROOT/current"
RELEASE="$RELEASES/$RELEASE_ID"
PREVIOUS=""
SWITCHED=0
LOCK="$APP_ROOT/.deploy.lock"

cleanup_on_error() {
  status=$?
  if (( status != 0 )); then
    if (( SWITCHED == 1 )) && [[ -n "$PREVIOUS" && -d "$PREVIOUS" ]]; then
      ln -s "$PREVIOUS" "$APP_ROOT/current.rollback"
      mv -Tf "$APP_ROOT/current.rollback" "$CURRENT"
      touch "$PASSENGER_RESTART_FILE"
      printf 'deploy: restored previous release %s\n' "$PREVIOUS" >&2
    elif (( SWITCHED == 1 )); then
      rm -f "$CURRENT"
      touch "$PASSENGER_RESTART_FILE"
      printf 'deploy: removed failed first release symlink\n' >&2
    fi
    rm -f "$APP_ROOT/current.next"
  fi
  rmdir "$LOCK" 2>/dev/null || true
  exit "$status"
}
trap cleanup_on_error EXIT

mkdir "$LOCK" 2>/dev/null || die "another deployment is running (or $LOCK is stale)"

command -v unzip >/dev/null || die "unzip is required on the hosting account"
command -v sha256sum >/dev/null || die "sha256sum is required on the hosting account"
command -v curl >/dev/null || die "curl is required on the hosting account"
command -v "$PYTHON" >/dev/null || die "Python command not found: $PYTHON"
[[ -f "$ARCHIVE" ]] || die "uploaded artifact not found: $ARCHIVE"
[[ -f "$SHARED/.env" ]] ||
  die "create $SHARED/.env before the first deployment (see docs/production-operations.md)"

mkdir -p \
  "$RELEASES" \
  "$SHARED/storage/scenarios" \
  "$SHARED/storage/media/avatars" \
  "$SHARED/backups" \
  "$SHARED/logs"
chmod 700 "$SHARED" "$SHARED/storage" "$SHARED/backups" "$SHARED/logs"
chmod 600 "$SHARED/.env"

ACTUAL_SHA=$(sha256sum "$ARCHIVE" | awk '{print $1}')
[[ "$ACTUAL_SHA" == "$EXPECTED_SHA" ]] || die "artifact checksum mismatch"
if unzip -Z1 "$ARCHIVE" | grep -Eq '(^|/)\.env$|(^|/)(storage|backups)(/|$)|\.(db|sqlite|sqlite3)$|(^/|(^|/)\.\.(/|$))'; then
  die "artifact contains a forbidden .env, storage, absolute, or traversal path"
fi
[[ ! -e "$RELEASE" ]] || die "release already exists: $RELEASE_ID"

mkdir "$RELEASE"
unzip -q "$ARCHIVE" -d "$RELEASE"
ln -s "$SHARED/.env" "$RELEASE/.env"
ln -s "$SHARED/storage" "$RELEASE/storage"
mkdir -p "$RELEASE/tmp"

"$PYTHON" -m venv "$RELEASE/.venv"
"$RELEASE/.venv/bin/python" -m pip install --disable-pip-version-check \
  --no-input --no-cache-dir -r "$RELEASE/requirements-production.txt"

# Back up before any schema mutation. A migration failure leaves CURRENT untouched.
"$RELEASE/.venv/bin/python" "$RELEASE/scripts/backup.py" \
  --destination "$SHARED/backups" --retention-days 14
(
  cd "$RELEASE"
  "$RELEASE/.venv/bin/python" -m flask --app passenger_wsgi:application db upgrade
  "$RELEASE/.venv/bin/python" scripts/release_check.py --base-url "$PUBLIC_BASE_URL"
)

if [[ -L "$CURRENT" ]]; then
  PREVIOUS=$(readlink -f "$CURRENT")
fi
ln -s "$RELEASE" "$APP_ROOT/current.next"
mv -Tf "$APP_ROOT/current.next" "$CURRENT"
SWITCHED=1
touch "$PASSENGER_RESTART_FILE"

ready=0
for delay in 1 2 3 5 8; do
  if curl --fail --silent --show-error --max-time 15 \
    "$PUBLIC_BASE_URL/health/ready" >/dev/null; then
    ready=1
    break
  fi
  sleep "$delay"
done
(( ready == 1 )) || die "public readiness check failed; rolling back application release"

SWITCHED=0
rm -f "$ARCHIVE"
printf 'deploy: release %s is healthy\n' "$RELEASE_ID"
