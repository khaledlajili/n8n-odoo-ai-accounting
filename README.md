# n8n + Odoo AI Accounting Assistant

A portfolio project demonstrating **human-in-the-loop AI automation** for accounts payable: Odoo Community Edition as the accounting source of truth, self-hosted n8n for orchestration, and a constrained AI Agent that can look up accounting data but cannot write to Odoo without explicit human approval.

Built with **only free and open-source software** — no paid APIs, no paid hosting.

---

## What this project proves

1. **AI can orchestrate accounting work safely.** The agent chooses tools based on intent, reads Odoo via narrow endpoints, and refuses every forbidden action.
2. **LLMs cannot be trusted with money math.** Every invoice amount is recalculated with `Decimal` arithmetic in code. The model never computes totals.
3. **Writes require human approval.** The agent can only *queue* a draft vendor bill for review; a human must approve it via a dedicated webhook before any `account.move` is created.
4. **Persistence and reproducibility matter.** Pinned Docker images, named volumes, deterministic validation, and a full test matrix.

---

## Architecture at a glance

```
Employee / Demo User
      │
      ▼
┌─────────────────────────────────────────────────────────┐
│ n8n Community 2.42.4  (orchestration only)              │
│                                                          │
│  WF01  Invoice intake → LLM extraction → validator       │
│  WF02  Supplier + PO matching against Odoo (read-only)   │
│  WF03  Human review → draft vendor bill (approval gate)  │
│  WF04  AI Agent → 6 constrained tools                    │
│  WF05  Exception handling + audit trail                  │
└─────────────────────────────────────────────────────────┘
      │                                  ▲
      ▼                                  │
┌─────────────────────┐      ┌─────────────────────────┐
│ Odoo 17 Community   │      │ Validator service       │
│ Contacts / Purchase │      │ (Python + FastAPI)      │
│ Accounting          │      │ - Decimal arithmetic    │
│                     │      │ - XML-RPC proxy to Odoo │
│ PostgreSQL 15 +     │      │ - review state (PG)     │
│ Odoo filestore      │      │ - `/tool/*` endpoints   │
└─────────────────────┘      └─────────────────────────┘
```

---

## The AI Agent's 6 tools

| Tool | Permission | What it does |
|---|---|---|
| `lookupSupplier` | read-only | Find supplier by name or VAT ID |
| `lookupPurchaseOrder` | read-only | Fetch PO header + lines |
| `invoiceProcessingStatus` | read-only | Report review status and matched bill |
| `vendorBillStatus` | read-only | Look up `account.move` state |
| `prepareDraftVendorBill` | **restricted write** | Queue a review — never writes Odoo |
| `sendToHumanReview` | controlled | Escalate — never approves |

**The agent has no tool that can post, pay, delete, or create a supplier.**

---

## Guarantees (verified, see `docs/SECURITY.md`)

- Every vendor bill requires explicit human approval before creation.
- No `account.move` is ever posted or paid by any workflow.
- All monetary amounts are recalculated with `Decimal` — the model's arithmetic is never trusted.
- Missing, ambiguous, or mismatched data routes to human review, never auto-resolves.
- Duplicate invoice + supplier pairs are detected before any draft is prepared.
- The agent treats invoice text as data, not instructions — prompt injection attempts are ignored.
- Every review decision is stored with reviewer, reason, and timestamp.

---

## Quick start

Requirements: Docker Engine 24+, Docker Compose v2, 8 GB RAM, 10 GB free disk.

```bash
git clone <this-repo> n8n-odoo-ai-accounting
cd n8n-odoo-ai-accounting

# 1. Environment
cp .env.example .env
# Fill in at least: GROQ_API_KEY, ODOO_MASTER_PASSWORD, all DB passwords
# (The .env bootstrap script in docs/SETUP.md generates secure random values.)

# 2. Start the stack
docker compose pull
docker compose up -d
sleep 30
docker compose ps

# 3. Create the Odoo database
#   Open http://localhost:8069/web/database/manager
#   Master password is ODOO_MASTER_PASSWORD from .env
#   Database: northstar   Demo data: unchecked

# 4. Seed synthetic data + create integration user
source .venv/bin/activate    # or create it: python3 -m venv .venv && .venv/bin/pip install reportlab pydantic
ODOO_PASSWORD='<admin-password>' python3 helpers/seed_data.py
#   Then in Odoo: create user n8n@northstar.local, generate API key
#   See docs/SETUP.md §Phase 2 for exact steps

# 5. Import workflows and run the demo
bash docs/DEMO_SCRIPT.md --dry-run 2>/dev/null || true
```

Full reproduction: **`docs/SETUP.md`**.
Demo runbook: **`docs/DEMO_SCRIPT.md`**.

---

## Test matrix

See **`docs/TEST_REPORT.md`** for the full per-phase matrix. Summary:

| Phase | What was tested | Result |
|---|---|---|
| 1 | Compose stack, volume persistence, restart | ✅ |
| 2 | Odoo DB, seed data, read-only integration user | ✅ |
| 3 | WF01 intake + LLM + deterministic validator (3 fixtures) | ✅ |
| 4 | WF02 supplier + PO matching (4 scenarios) | ✅ |
| 5 | WF03 human review → draft bill (idempotent, no post/pay) | ✅ |
| 6 | WF04 AI Agent (12 behaviour cases, safety verified at DB level) | ✅ |

---

## Known limitations

See **`docs/LIMITATIONS.md`**. Short version:

- **Groq free tier limits** the agent to ~30 requests/minute and 8,000 tokens/minute per model.
- **Synthetic data only** — no real invoices, no real supplier PII.
- **`postgres:15.7`** is used but n8n 2.x officially supports 17+ (16 on compatibility). Documented as a known constraint.
- **Public hosting is optional** — the plan requires local Docker for durability. Free-tier hosting breaks Odoo's filestore persistence.

---

## Repository layout

```
n8n-odoo-ai-accounting/
├── README.md                  ← this file
├── PLAN.md                    ← the 15-section build plan
├── compose.yaml               ← PostgreSQL + Odoo + n8n + validator
├── .env.example               ← placeholders only
├── docs/
│   ├── ARCHITECTURE.md        ← diagram + trust boundaries
│   ├── SETUP.md               ← from-zero reproduction
│   ├── DEMO_SCRIPT.md         ← 2–3 minute demo
│   ├── SECURITY.md            ← threat model + per-guarantee evidence
│   ├── LIMITATIONS.md         ← honest constraints
│   └── TEST_REPORT.md         ← consolidated across phases 1–6
├── workflows/                 ← exported n8n workflow JSON
├── helpers/                   ← Python validation + Odoo proxy
│   ├── extraction/            ← (reserved)
│   ├── matching/              ← deterministic invoice matcher
│   └── validation/            ← Pydantic validators + FastAPI service
├── sample-data/
│   ├── invoices/              ← 3 synthetic PDFs (clean, mismatch, missing)
│   └── expected-results/
└── scripts/
    ├── n8n-import-workflow.sh
    ├── n8n-import-credentials.sh
    ├── test-wf01.sh
    ├── test-wf04.sh
    └── backup-restore.sh
```

---

## License

Free and open-source. Synthetic data only. No real-world accounting usage intended.
