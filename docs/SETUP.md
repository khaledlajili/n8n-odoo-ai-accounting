# Setup — from zero to a working demo

## Requirements

| Requirement | Minimum | Recommended |
|---|---|---|
| OS | Ubuntu 22.04 / 24.04, or any Docker-capable Linux | Ubuntu 24.04 |
| CPU | 2 cores | 4 cores |
| RAM | 8 GB | 16 GB |
| Disk | 10 GB free | 20 GB free |
| Docker | Engine 24+, Compose v2 | latest stable |

## 1. Clone and initialize

```bash
git clone <repo> n8n-odoo-ai-accounting
cd n8n-odoo-ai-accounting

cp .env.example .env
```

Edit `.env` and fill in:

- `POSTGRES_PASSWORD` — superuser DB password
- `ODOO_DB_PASSWORD`, `ODOO_MASTER_PASSWORD` — Odoo's DB role + database-manager password
- `N8N_DB_PASSWORD`, `N8N_ENCRYPTION_KEY` — n8n's DB role + encryption key (32+ random bytes)
- `GROQ_API_KEY` — from https://console.groq.com/keys
- `GROQ_MODEL` — `openai/gpt-oss-120b`

Or generate all secrets with the bootstrap in `PLAN.md` §Phase 1 Step 5.

## 2. Start the stack

```bash
docker compose pull
docker compose up -d
sleep 30
docker compose ps
```

Expected:

- `northstar-postgres` — healthy
- `northstar-odoo` — up
- `northstar-n8n` — up
- `northstar-validator` — up

## 3. Create the Odoo database

1. Open <http://localhost:8069/web/database/manager>
2. Master password: `ODOO_MASTER_PASSWORD` from `.env`
3. Fill in:
   - **Database:** `northstar`
   - **Email:** `admin@northstar.local`
   - **Password:** strong password (write it down)
   - **Demo data:** unchecked
4. Click **Create Database**

## 4. Install Odoo modules

In Odoo → Settings → Activate developer mode → Apps → Update Apps List.

Install in this order:

1. **Contacts** (`contacts`)
2. **Invoicing** (`account`)
3. **Purchase** (`purchase`)

## 5. Seed synthetic data

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install reportlab pydantic

ODOO_PASSWORD='<admin-password>' python3 helpers/seed_data.py
```

This creates:
- 5 suppliers with synthetic VAT IDs (`DEMO-TAX-001` … `DEMO-TAX-005`)
- 5 products (`PROD-PAPER`, `PROD-TONER`, …)
- 5 purchase orders (`PO-204` … `PO-208`), all in EUR

## 6. Create the integration user

1. In Odoo, open **Settings → Users & Companies → Users → New**
2. **Name:** `n8n Integration`
3. **Email:** `n8n@northstar.local`
4. **Password:** strong password
5. **User Type:** Internal User
6. **Access Rights:** add exactly these groups
   - Purchase / User
   - Invoicing / Billing
7. Save.
8. Log out and log in as `n8n@northstar.local`
9. Avatar → Preferences → Account Security → New API Key → name `n8n integration` → copy the key
10. Save it to `.odoo_api_key` locally:
    ```bash
    printf '%s' '<paste-key>' > .odoo_api_key
    chmod 600 .odoo_api_key
    ```
11. Verify the user **cannot** create partners:
    ```bash
    ODOO_API_KEY="$(cat .odoo_api_key)" python3 helpers/test_odoo_lookup.py
    ```
    Expected: `OK: partner creation blocked`.

## 7. Import n8n credentials

```bash
set -a; source .env; set +a
./scripts/n8n-import-credentials.sh
```

Or manually:

```bash
# Groq
python3 - <<'PY' > /tmp/groq.json
import json, os
print(json.dumps([{"id":"groq-cred","name":"Groq account","type":"groqApi",
  "data":{"apiKey": os.environ["GROQ_API_KEY"]}}]))
PY
docker cp /tmp/groq.json northstar-n8n:/home/node/groq.json
docker exec -u node northstar-n8n n8n import:credentials --input=/home/node/groq.json

# OpenRouter (optional, used by WF01 fallback)
# Same pattern with type "openAiApi", url "https://openrouter.ai/api/v1"
```

## 8. Import workflows

```bash
# WF01, WF02, WF03 as usual
./scripts/n8n-import-workflow.sh workflows/WF01_invoice_intake.json
./scripts/n8n-import-workflow.sh workflows/WF02_supplier_po_matching.json
./scripts/n8n-import-workflow.sh workflows/WF03_human_review_draft_bill.json

# WF04 requires its TOOL sub-workflow to be imported and PUBLISHED first
./scripts/n8n-import-workflow.sh workflows/TOOL_accounting_actions.json
SUB_ID=$(docker exec -i northstar-postgres psql -U n8n_user -d n8n_db -t -A \
  -c "SELECT id FROM workflow_entity WHERE name='TOOL - Accounting Assistant Actions' LIMIT 1;" | tr -d '[:space:]')
docker exec -u node northstar-n8n n8n publish:workflow --id="$SUB_ID"
./scripts/n8n-import-workflow.sh workflows/WF04_accounting_agent.json
```

## 9. Activate and test

```bash
# Activate all
for wf in wf01-invoice-intake wf02-supplier-po-matching wf03-human-review-draft-bill; do
  docker exec -u node northstar-n8n n8n publish:workflow --id="$wf" 2>/dev/null || \
  docker exec -u node northstar-n8n n8n update:workflow --id="$wf" --active=true 2>/dev/null || true
done
WF04_ID=$(docker exec -i northstar-postgres psql -U n8n_user -d n8n_db -t -A \
  -c "SELECT id FROM workflow_entity WHERE name='WF04 - Accounting Assistant Agent' LIMIT 1;" | tr -d '[:space:]')
docker exec -u node northstar-n8n n8n publish:workflow --id="$WF04_ID"

# Restart so webhooks register
docker compose restart n8n
sleep 20

# Smoke tests
./scripts/test-wf01.sh
./scripts/test-wf04.sh
```

## Troubleshooting

| Symptom | Fix |
|---|---|
| Odoo "database manager" returns 200 but you can't create DB | Check `ODOO_MASTER_PASSWORD` in `.env` matches `admin_passwd` in `docker/odoo/custom-entrypoint.sh` |
| n8n webhook 404 | Workflow not active. Run the activation loop above, then restart. |
| `supplyData` error on `toolWorkflow` | Sub-workflow not published. `n8n publish:workflow --id=<TOOL id>` |
| Groq 429 rate limit | Reduce harness speed: `SLEEP_BETWEEN_ASKS=25 ./scripts/test-wf04.sh` |
| `workflow_published_version` FK error on delete | Unpublish first: `n8n unpublish:workflow --id=<id>` |

## Versions (pinned)

| Component | Version | Why |
|---|---|---|
| PostgreSQL | `15.7` | Stable; **note:** n8n 2.x officially supports 17+. See `docs/LIMITATIONS.md`. |
| Odoo | `17.0` | Latest Community series with stable external API. |
| n8n | `2.42.4` | Contains `supplyData` fix (2.8.4) and expression fix (2.35.0). |
| Validator | Python `3.12-slim` | FastAPI + Pydantic v2 + psycopg2. |
| Groq model | `openai/gpt-oss-120b` | Free tier, native tool calling. |
| OpenRouter model | `meta-llama/llama-3.3-70b-instruct:free` | Fallback for WF01 only. |
