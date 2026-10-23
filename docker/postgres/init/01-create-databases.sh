#!/bin/bash
# Runs once on first init of the PostgreSQL data volume.
# Env vars (N8N_DB_*, ODOO_DB_*) are provided by the postgres service in compose.yaml.
set -euo pipefail

psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" <<-EOSQL
    -- n8n role and database
    CREATE ROLE ${N8N_DB_USER} WITH LOGIN PASSWORD '${N8N_DB_PASSWORD}';
    CREATE DATABASE ${N8N_DB_NAME} OWNER ${N8N_DB_USER};

    -- Odoo role (CREATEDB so Odoo can create its database via the web manager)
    CREATE ROLE ${ODOO_DB_USER} WITH LOGIN CREATEDB PASSWORD '${ODOO_DB_PASSWORD}';
EOSQL

echo "[init] Created roles '${N8N_DB_USER}' and '${ODOO_DB_USER}', database '${N8N_DB_NAME}'."
