# n8n + Odoo AI Accounting Assistant

Portfolio project: connect **Odoo Community 17** with self-hosted **n8n Community** to build an AI-assisted, human-in-the-loop invoice pipeline for the fictional company **Northstar Trading**.

> Status: **Phase 1 — Local foundation**

## Quick start

```bash
cp .env.example .env       # or run the .env bootstrap in docs/SETUP.md
docker compose pull
docker compose up -d
```

- Odoo: <http://localhost:8069>
- n8n:  <http://localhost:5678>

## Documentation

- [Plan](PLAN.md)
- [Architecture](docs/ARCHITECTURE.md)
- [Setup](docs/SETUP.md)
- [Demo script](docs/DEMO_SCRIPT.md)
- [Security](docs/SECURITY.md)
- [Test report](docs/TEST_REPORT.md)

## Guarantees

- Synthetic data only. No real invoices, no real personal data.
- Odoo is the source of truth. The AI agent never touches PostgreSQL.
- All accounting calculations are deterministic (code, not the model).
- Every vendor bill requires explicit human approval before creation.
- No paid APIs, no paid hosting.
