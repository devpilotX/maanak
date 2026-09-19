#!/usr/bin/env bash
# Restore a Maanak backup over the current deployment.
#
#   bash scripts/restore.sh backup/20260919T190000Z --i-understand-this-destroys-current-data
#
# This drops and recreates the database and overwrites object storage. It refuses to run
# without the confirmation flag, because a restore script that can be invoked by accident is
# worse than no restore script.
#
# Afterwards, prove it worked rather than assuming:
#
#   docker compose run --rm --no-deps -v "$PWD:/repo" -e PYTHONPATH=/repo/api migrate \
#     python /repo/api/scripts/verify_restore.py \
#     --expect /repo/backup/<stamp>/audit-chain-at-backup.json
set -euo pipefail

BUCKETS=(maanak-originals maanak-derivatives maanak-reports)
STAGING=/tmp/maanak-restore-staging
CONFIRMED=0
FROM=""

while [ $# -gt 0 ]; do
  case "$1" in
    --i-understand-this-destroys-current-data) CONFIRMED=1; shift ;;
    -h|--help) sed -n '2,15p' "$0"; exit 0 ;;
    *) FROM="$1"; shift ;;
  esac
done

cd "$(dirname "$0")/.."

[ -n "$FROM" ] || { echo "usage: bash scripts/restore.sh <backup-dir> --i-understand-this-destroys-current-data" >&2; exit 2; }
[ -d "$FROM" ] || { echo "no such backup directory: $FROM" >&2; exit 2; }
[ -f "$FROM/maanak.dump" ] || { echo "no maanak.dump in $FROM" >&2; exit 2; }

if [ "$CONFIRMED" -ne 1 ]; then
  echo "Refusing to run." >&2
  echo "This drops and recreates the database and overwrites object storage." >&2
  echo "Re-run with --i-understand-this-destroys-current-data if that is what you want." >&2
  exit 3
fi

USER_NAME="${POSTGRES_USER:-maanak}"
DB_NAME="${POSTGRES_DB:-maanak}"

echo "restoring from $FROM"

if [ -f "$FROM/manifest.sha256" ]; then
  printf '  %-52s ' "backup files match their checksums"
  if ( cd "$FROM" && sha256sum --quiet --check manifest.sha256 2>/dev/null ); then
    echo ok
  else
    echo "FAILED"
    echo "  the backup is damaged. Restoring it would spread the damage." >&2
    exit 1
  fi
fi

printf '  %-52s ' "infrastructure up"
docker compose up -d --wait db redis minio >/dev/null 2>&1 && echo ok

# The database. --clean --if-exists so a partially initialised database is replaced rather
# than merged, which would leave a mixture of two deployments.
printf '  %-52s ' "drop and recreate the database"
docker compose exec -T db psql -U "$USER_NAME" -d postgres -v ON_ERROR_STOP=1 \
  -c "drop database if exists $DB_NAME with (force)" -c "create database $DB_NAME owner $USER_NAME" \
  >/dev/null 2>&1 && echo ok

printf '  %-52s ' "restore the dump"
if docker compose exec -T db pg_restore -U "$USER_NAME" -d "$DB_NAME" --no-owner --no-privileges \
     < "$FROM/maanak.dump" >/dev/null 2>/tmp/maanak-restore.err; then
  echo ok
else
  # pg_restore warns about extensions and ownership on a clean database; those are not
  # failures. A real failure leaves no tables behind, which is what is checked.
  tables=$(docker compose exec -T db psql -U "$USER_NAME" -d "$DB_NAME" -tAc \
    "select count(*) from information_schema.tables where table_schema='public'" 2>/dev/null | tr -d '[:space:]')
  if [ "${tables:-0}" -gt 20 ]; then
    echo "ok (with warnings)"
  else
    echo "FAILED"
    head -5 /tmp/maanak-restore.err >&2
    exit 1
  fi
fi

# Object storage.
if [ -d "$FROM/objects" ] && [ -n "$(ls -A "$FROM/objects" 2>/dev/null)" ]; then
  printf '  %-52s ' "object storage alias"
  docker compose exec -T minio mc alias set local http://127.0.0.1:9000 \
    "${S3_ACCESS_KEY:?set S3_ACCESS_KEY}" "${S3_SECRET_KEY:?set S3_SECRET_KEY}" >/dev/null 2>&1 && echo ok

  docker compose exec -T minio rm -rf "$STAGING" >/dev/null 2>&1 || true
  docker compose exec -T minio mkdir -p "$STAGING" >/dev/null 2>&1 || true
  printf '  %-52s ' "copy objects into the container"
  docker compose cp "$FROM/objects/." "minio:$STAGING/" >/dev/null 2>&1 && echo ok

  for bucket in "${BUCKETS[@]}"; do
    printf '  %-52s ' "restore $bucket"
    docker compose exec -T minio mc mb --ignore-existing "local/$bucket" >/dev/null 2>&1 || true
    if docker compose exec -T minio test -d "$STAGING/$bucket" >/dev/null 2>&1; then
      docker compose exec -T minio mc mirror --quiet --overwrite \
        "$STAGING/$bucket" "local/$bucket" >/dev/null 2>&1 && echo ok || echo "FAILED"
    else
      echo "ok (nothing in the backup)"
    fi
  done
  docker compose exec -T minio rm -rf "$STAGING" >/dev/null 2>&1 || true
else
  echo "  no objects in this backup, skipping object storage"
fi

printf '  %-52s ' "application up"
docker compose up -d api worker web >/dev/null 2>&1 && echo ok
# nginx resolves the API address once at startup, so it has to follow a recreate.
docker compose restart web >/dev/null 2>&1 || true

echo
echo "restored. NOT yet verified. Run:"
echo "  docker compose run --rm --no-deps -v \"\$PWD:/repo\" -e PYTHONPATH=/repo/api migrate \\"
echo "    python /repo/api/scripts/verify_restore.py \\"
echo "      --expect /repo/$FROM/audit-chain-at-backup.json"
