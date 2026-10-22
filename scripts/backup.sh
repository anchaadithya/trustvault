#!/usr/bin/env bash
# Encrypted backup of the database AND the private file store. Requires: pg_dump, tar, gpg.
# Usage: DB_NAME=... DB_USER=... PRIVATE_STORAGE_ROOT=... GPG_RECIPIENT=you@example.com ./scripts/backup.sh /backups
set -euo pipefail
OUT="${1:?backup directory}"; STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
umask 077; mkdir -p "$OUT"
pg_dump -h "${DB_HOST:-localhost}" -U "$DB_USER" "$DB_NAME" | gpg --encrypt --recipient "$GPG_RECIPIENT" > "$OUT/db-$STAMP.sql.gpg"
tar -C "$PRIVATE_STORAGE_ROOT" -cf - . | gpg --encrypt --recipient "$GPG_RECIPIENT" > "$OUT/files-$STAMP.tar.gpg"
echo "Backup written to $OUT ($STAMP). Retention is NOT automatic: delete files older than 30 days yourself."
