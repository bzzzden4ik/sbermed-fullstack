#!/usr/bin/env bash
# Daily backup of the SIRIUS database and uploaded files; keeps the last 7 days.
# Installed in root's crontab: 30 3 * * * /opt/sirius/app/deploy/backup.sh
set -euo pipefail
DEST=/var/backups/sirius
STAMP=$(date +%F)
mkdir -p "$DEST"
chmod 700 "$DEST"
sudo -u postgres pg_dump -Fc sirius > "$DEST/db-$STAMP.dump"
tar -czf "$DEST/files-$STAMP.tar.gz" -C /opt/sirius/app/backend/hackathon-hospital uploads private_uploads 2>/dev/null || true
find "$DEST" -type f -mtime +7 -delete
echo "$(date -Is) backup ok: $(du -sh "$DEST" | cut -f1)"
