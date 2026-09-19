#!/usr/bin/env bash
# Back up a running Maanak deployment: database, object storage, and the audit chain head.
#
#   bash scripts/backup.sh                     # writes backup/<timestamp>/
#   bash scripts/backup.sh --into /mnt/backups # somewhere else
#   bash scripts/backup.sh --include-env       # also copies .env, which holds every secret
#
# The chain head is the step docs/BACKUP_RESTORE.md calls "the one people skip". It is read
# straight from the database rather than through the API, so a backup needs no credentials
# and cannot fail because a session expired.
set -euo pipefail

BUCKETS=(maanak-originals maanak-derivatives maanak-reports)
STAGING=/tmp/maanak-backup-staging
INTO=""
INCLUDE_ENV=0

while [ $# -gt 0 ]; do
  case "$1" in
    --into) INTO="${2:?--into needs a directory}"; shift 2 ;;
    --include-env) INCLUDE_ENV=1; shift ;;
    -h|--help) sed -n '2,10p' "$0"; exit 0 ;;
    *) echo "unknown argument: $1" >&2; exit 2 ;;
  esac
done

cd "$(dirname "$0")/.."
STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
OUT="${INTO:-backup}/$STAMP"
mkdir -p "$OUT/objects"

ok=0
fail=0
step() { printf '  %-52s ' "$1"; }
pass() { printf 'ok\n'; ok=$((ok + 1)); }
died() { printf 'FAILED %s\n' "${1:-}"; fail=$((fail + 1)); }

echo "backing up into $OUT"

# The database. Custom format so a restore can be selective.
step "database dump"
if docker compose exec -T db pg_dump -U "${POSTGRES_USER:-maanak}" -d "${POSTGRES_DB:-maanak}" -Fc \
     > "$OUT/maanak.dump" 2>"$OUT/pg_dump.err"; then
  size=$(wc -c < "$OUT/maanak.dump")
  if [ "$size" -lt 4096 ]; then
    died "only $size bytes, which is too small to be a real dump"
  else
    pass
    echo "      $(numfmt --to=iec "$size" 2>/dev/null || echo "$size bytes")"
  fi
else
  died "$(head -1 "$OUT/pg_dump.err" 2>/dev/null)"
fi

# Object storage. mc ships inside the MinIO image.
step "object storage alias"
if docker compose exec -T minio mc alias set local http://127.0.0.1:9000 \
     "${S3_ACCESS_KEY:?set S3_ACCESS_KEY}" "${S3_SECRET_KEY:?set S3_SECRET_KEY}" >/dev/null 2>&1; then
  pass
else
  died "could not reach MinIO"
fi

docker compose exec -T minio rm -rf "$STAGING" >/dev/null 2>&1 || true
for bucket in "${BUCKETS[@]}"; do
  step "mirror $bucket"
  if docker compose exec -T minio mc mirror --quiet --overwrite \
       "local/$bucket" "$STAGING/$bucket" >/dev/null 2>&1; then
    pass
  else
    # An empty bucket is not a failure. A missing one is.
    if docker compose exec -T minio mc ls "local/$bucket" >/dev/null 2>&1; then
      pass
    else
      died "bucket missing"
    fi
  fi
done

step "copy objects to the host"
if docker compose cp "minio:$STAGING/." "$OUT/objects/" >/dev/null 2>&1; then
  pass
  echo "      $(find "$OUT/objects" -type f | wc -l) files"
else
  died "compose cp"
fi
docker compose exec -T minio rm -rf "$STAGING" >/dev/null 2>&1 || true

# The audit chain head. Recorded so a later restore can be proved to hold the same trail
# rather than a truncated copy.
step "audit chain head"
head_row=$(docker compose exec -T db psql -U "${POSTGRES_USER:-maanak}" -d "${POSTGRES_DB:-maanak}" \
  -tAF'|' -c "select coalesce(max(sequence),0), count(*) from audit_events where chain_key='global'" 2>/dev/null || true)
head_hash=$(docker compose exec -T db psql -U "${POSTGRES_USER:-maanak}" -d "${POSTGRES_DB:-maanak}" \
  -tAc "select event_hash from audit_events where chain_key='global' order by sequence desc limit 1" 2>/dev/null || true)
head_seq="${head_row%%|*}"
head_count="${head_row##*|}"
head_seq="$(echo "$head_seq" | tr -d '[:space:]')"
head_count="$(echo "$head_count" | tr -d '[:space:]')"
head_hash="$(echo "$head_hash" | tr -d '[:space:]')"
if [ -n "$head_seq" ]; then
  cat > "$OUT/audit-chain-at-backup.json" <<JSON
{
  "chain_key": "global",
  "head_sequence": ${head_seq:-0},
  "head_hash": "${head_hash}",
  "event_count": ${head_count:-0},
  "taken_at": "$STAMP"
}
JSON
  pass
  echo "      sequence $head_seq, $head_count events, hash ${head_hash:0:16}"
else
  died "could not read the chain"
fi

# Configuration. It holds the KMS key, without which restored objects cannot be decrypted,
# and every other secret in the system. Opt-in on purpose.
if [ "$INCLUDE_ENV" -eq 1 ]; then
  step ".env copied (--include-env)"
  cp .env "$OUT/env.backup" && chmod 600 "$OUT/env.backup" && pass || died
  echo "      WARNING: $OUT/env.backup holds every secret in this deployment,"
  echo "      including MINIO_KMS_SECRET_KEY and JWT_SECRET. Store it where secrets"
  echo "      belong, not beside the dumps, and never in version control."
else
  echo "  .env NOT copied. Objects are encrypted at rest and cannot be read"
  echo "      without MINIO_KMS_SECRET_KEY. Capture it separately, or re-run"
  echo "      with --include-env if this backup target is already a secret store."
fi

# Written during the dump step and only useful if it failed. Removed before the manifest,
# because a manifest listing a file that is then deleted makes every later restore refuse.
rm -f "$OUT/pg_dump.err"

step "manifest with checksums"
{
  echo "# Maanak backup $STAMP"
  echo "# Verify a restore with api/scripts/verify_restore.py --expect $OUT/audit-chain-at-backup.json"
  ( cd "$OUT" && find . -type f ! -name manifest.sha256 -exec sha256sum {} + | sort -k2 )
} > "$OUT/manifest.sha256" && pass

echo
echo "backup steps passed: $ok, failed: $fail"
if [ "$fail" -gt 0 ]; then
  echo "this backup is not trustworthy. Do not rely on it." >&2
  exit 1
fi
echo "written to $OUT"
