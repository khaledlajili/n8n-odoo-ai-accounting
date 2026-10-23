# Architecture

See `PLAN.md` §2 for the canonical diagram.

## Phase 1 services

| Service  | Image               | Port (host) | Persistent volume |
|----------|---------------------|-------------|-------------------|
| postgres | `postgres:15.7`     | (internal)  | `postgres_data`   |
| odoo     | `odoo:17.0`         | `8069`      | `odoo_data`       |
| n8n      | `n8nio/n8n:1.70.3`  | `5678`      | `n8n_data`        |

## Boundaries

- One PostgreSQL server, **two separate roles/databases**: `odoo_user`/`northstar` (created later via Odoo UI) and `n8n_user`/`n8n_db` (created by the init script).
- n8n state lives in PostgreSQL (`DB_TYPE=postgresdb`), not in SQLite, so it survives container replacement.
- Odoo's **filestore** lives on `odoo_data`; losing it means losing attachments — back it up with the DB.
- The AI agent only reaches Odoo through narrow n8n tool nodes. It never gets SQL, shell, or unrestricted HTTP.

## Volumes on the host

```bash
docker volume ls | grep northstar
# northstar_postgres_data
# northstar_odoo_data
# northstar_n8n_data
```
