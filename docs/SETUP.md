# Setup

## Prerequisites

- Ubuntu 22.04 / 24.04 (or any Docker-capable Linux)
- Docker Engine 24+ and Docker Compose v2
- 4 GB RAM minimum, 8 GB recommended
- ~5 GB free disk

## First start

```bash
cp .env.example .env
# Edit .env and set strong passwords, or use the bootstrap snippet in PLAN.md Phase 1 Step 5.
docker compose pull
docker compose up -d
docker compose ps
```

## Endpoints

| Service | URL |
|---|---|
| Odoo    | http://localhost:8069 |
| n8n     | http://localhost:5678 |

## Reset (DESTROYS ALL DATA)

```bash
docker compose down -v   # -v removes named volumes
```

## Backup / restore (to be completed in Phase 7)

- PostgreSQL: `docker compose exec -T postgres pg_dump -U postgres -Fc northstar > backup/northstar.dump`
- Odoo filestore: `docker run --rm -v northstar_odoo_data:/data -v "$PWD/backup":/backup alpine tar czf /backup/odoo_filestore.tgz -C /data .`
- n8n: export workflows from the editor + back up `northstar_n8n_data`.

## Phase 2 — Verified Odoo API details

- **Odoo version:** 17.0 (Docker image `odoo:17.0`)
- **Database:** `northstar`
- **Authentication:** XML-RPC and JSON-RPC both work against `http://localhost:8069` (host) and `http://odoo:8069` (inside the Docker network).
- **Integration user:** `n8n@northstar.local` — Internal User + Purchase/User + Invoicing/Billing. Partner creation is **blocked** (verified).
- **API key:** generated under Preferences → Account Security → New API Key.

### Confirmed read paths

| Model | Method | Fields used |
|---|---|---|
| `res.partner` | `search_read` | `id`, `name`, `vat` |
| `purchase.order` | `search_read` | `id`, `name`, `partner_id`, `state`, `amount_total` |

### Confirmed write behaviour

| Operation | Result |
|---|---|
| `res.partner.create` as integration user | **Blocked** (insufficient access) |
| `account.move.create` | Not tested yet — Phase 5 |

### n8n connection

- **Site URL inside Docker:** `http://odoo:8069`
- **Site URL from host:** `http://localhost:8069`
- **Credential type:** Odoo, API Key authentication.
