#!/usr/bin/env bash
# Backup / restore PostgreSQL + Odoo filestore + n8n workflows.
# Usage:
#   ./scripts/backup-restore.sh backup
#   ./scripts/backup-restore.sh restore <backup-dir>
set -euo pipefail
cd "$(dirname "$0")/.."

ACTION="${1:-}"
STAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_ROOT="${BACKUP_ROOT:-backups}"

backup() {
    local dir="${BACKUP_ROOT}/${STAMP}"
    mkdir -p "$dir"
    echo "→ Backing up to $dir"

    echo "  PostgreSQL (all databases)..."
    docker exec -i northstar-postgres pg_dumpall -U postgres \
        | gzip > "$dir/postgres-all.sql.gz"

    echo "  Odoo filestore..."
    docker run --rm -v northstar_odoo_data:/data:ro -v "$PWD/$dir":/backup alpine \
        tar czf /backup/odoo_filestore.tgz -C /data . 2>/dev/null

    echo "  n8n workflows..."
    docker exec -u node northstar-n8n n8n export:workflow --all \
        --output=/home/node/wf-backup.json >/dev/null 2>&1 || true
    docker cp northstar-n8n:/home/node/wf-backup.json \
        "$dir/n8n-workflows.json" 2>/dev/null || true
    docker exec -u root northstar-n8n rm -f /home/node/wf-backup.json 2>/dev/null || true

    echo "  n8n credentials (encrypted by N8N_ENCRYPTION_KEY)..."
    docker exec -u node northstar-n8n n8n export:credentials --all \
        --output=/home/node/cr-backup.json >/dev/null 2>&1 || true
    docker cp northstar-n8n:/home/node/cr-backup.json \
        "$dir/n8n-credentials.json" 2>/dev/null || true
    docker exec -u root northstar-n8n rm -f /home/node/cr-backup.json 2>/dev/null || true

    echo "  .env snapshot (secrets — store securely, never commit)..."
    cp .env "$dir/env.snapshot"
    chmod 600 "$dir/env.snapshot"

    echo "✓ Backup complete: $dir"
    echo "  Size: $(du -sh "$dir" | cut -f1)"
}

restore() {
    local dir="${1:-}"
    if [ -z "$dir" ] || [ ! -d "$dir" ]; then
        echo "Usage: $0 restore <backup-dir>"
        exit 1
    fi

    echo "⚠ This will REPLACE the current PostgreSQL data, Odoo filestore, and n8n state."
    read -p "Type 'yes' to continue: " confirm
    [ "$confirm" = "yes" ] || { echo "Aborted."; exit 1; }

    echo "→ Stopping n8n and Odoo (postgres stays up to receive data)..."
    docker compose stop n8n odoo

    echo "  Restoring PostgreSQL..."
    gunzip -c "$dir/postgres-all.sql.gz" \
        | docker exec -i northstar-postgres psql -U postgres >/dev/null

    echo "  Restoring Odoo filestore..."
    docker run --rm -v northstar_odoo_data:/data -v "$PWD/$dir":/backup alpine \
        sh -c "rm -rf /data/* && tar xzf /backup/odoo_filestore.tgz -C /data"

    echo "  Restoring n8n workflows..."
    if [ -f "$dir/n8n-workflows.json" ]; then
        docker cp "$dir/n8n-workflows.json" northstar-n8n:/home/node/wf.json
        docker exec -u node northstar-n8n n8n import:workflow --input=/home/node/wf.json || true
        docker exec -u root northstar-n8n rm -f /home/node/wf.json || true
    fi

    echo "  Starting services..."
    docker compose up -d
    sleep 20
    docker compose ps
    echo "✓ Restore complete. Verify: open http://localhost:8069 and http://localhost:5678"
}

case "$ACTION" in
    backup)   backup ;;
    restore)  restore "${2:-}" ;;
    *)        echo "Usage: $0 {backup|restore <dir>}"; exit 1 ;;
esac
