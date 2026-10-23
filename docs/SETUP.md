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
