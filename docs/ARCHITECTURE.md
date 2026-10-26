# Architecture

## Canonical diagram

```
                 ┌──────────────────────────────────────────┐
                 │  Employee / Demo User                    │
                 │  (uploads PDF, asks agent questions)     │
                 └──────────────┬───────────────────────────┘
                                │
                                ▼
┌───────────────────────────────────────────────────────────────────┐
│ n8n Community 2.42.4                                              │
│                                                                    │
│  WF01  Invoice intake                                             │
│    ├─ Webhook: POST /webhook/invoice-intake                       │
│    ├─ Extract PDF → LLM extraction (Groq gpt-oss-120b)             │
│    ├─ Validator: POST /validate (Decimal + Pydantic)              │
│    └─ Routes: READY_FOR_MATCH | NEEDS_REVIEW | REJECTED           │
│                                                                    │
│  WF02  Supplier + PO matching                                     │
│    ├─ Webhook: POST /webhook/wf02-match                           │
│    ├─ Lookup supplier (VAT, then name) via XML-RPC proxy          │
│    ├─ Lookup PO by name                                           │
│    ├─ Validate currency, partner consistency, totals              │
│    ├─ Routes: MATCHED | NEEDS_REVIEW | REJECTED                   │
│    └─ On MATCHED: auto-queue a review row in PostgreSQL           │
│                                                                    │
│  WF03  Human review + draft vendor bill                           │
│    ├─ Webhook: POST /webhook/wf03                                 │
│    │    action=prepare → creates pending review (idempotent)       │
│    │    action=decide → records approve/reject                    │
│    └─ On approve: creates ONE draft account.move via XML-RPC proxy │
│        (never posts, never pays, never duplicates)                 │
│                                                                    │
│  WF04  AI Agent                                                   │
│    ├─ Webhook: POST /webhook/wf04-agent                           │
│    ├─ Groq model → 6 toolWorkflow nodes                            │
│    │   ├─ lookupSupplier           (read-only)                    │
│    │   ├─ lookupPurchaseOrder      (read-only)                    │
│    │   ├─ invoiceProcessingStatus  (read-only)                    │
│    │   ├─ vendorBillStatus         (read-only)                    │
│    │   ├─ prepareDraftVendorBill   (queue review only)            │
│    │   └─ sendToHumanReview        (queue review only)            │
│    └─ Sub-workflow: TOOL - Accounting Assistant Actions            │
│        (switch by `action` → one of 6 HTTP calls)                  │
│                                                                    │
│  WF05  Exceptions + audit trail (Phase 7+ — stub)                   │
└───────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌────────────────────────────────────────────────────────────────────┐
│ Validator service (Python 3.12 + FastAPI)                          │
│                                                                    │
│  POST /validate              Decimal + Pydantic invoice validator  │
│  POST /match                 Deterministic supplier/PO matcher     │
│  POST /odoo/{search_read,search,create,read,po_with_lines}         │
│  POST /review/{prepare,decide,get,find,prepare_from_request}       │
│  POST /tool/lookup_supplier                                        │
│  POST /tool/lookup_purchase_order                                  │
│  POST /tool/invoice_status                                         │
│  POST /tool/bill_status                                            │
│  POST /tool/prepare_draft                                          │
│  POST /tool/escalate                                               │
└────────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌────────────────────────────────────────────────────────────────────┐
│ Odoo 17 Community                                                  │
│   Contacts  ·  Purchase  ·  Invoicing (account)                    │
│   PostgreSQL 15.7 (two roles: odoo_user, n8n_user)                 │
│   Filestore on named volume odoo_data                              │
└────────────────────────────────────────────────────────────────────┘
```

## Trust boundaries

| Boundary | Rule |
|---|---|
| **LLM ↔ Odoo** | Never direct. The LLM only sees tool results, never raw Odoo responses. |
| **LLM ↔ PostgreSQL** | Never direct. The LLM has no SQL tool. |
| **LLM ↔ invoice text** | LLM treats invoice text as untrusted data. Prompt injection defence is in the system prompt and validated by test case. |
| **Amounts** | The LLM never computes a total. The validator recomputes with `Decimal`. If they differ by more than 2 cents, the invoice routes to human review. |
| **Writes** | Only WF03 can write to `account.move`. WF03 requires a human `approve` call. The agent's tools can queue a review, never approve it. |
| **Duplicate protection** | `request_id` has a `UNIQUE` constraint in `invoice_reviews`. Approving the same review twice returns the existing bill — no duplicate is ever created. |

## Phase mapping

| Phase | Workflows | Key files |
|---|---|---|
| 1 | (infrastructure) | `compose.yaml`, `.env`, `docker/` |
| 2 | (Odoo config) | `helpers/seed_data.py`, `helpers/test_odoo_lookup.py` |
| 3 | WF01 | `workflows/WF01_*.json`, `helpers/validation/validate_invoice.py` |
| 4 | WF02 | `workflows/WF02_*.json`, `helpers/matching/match_invoice.py` |
| 5 | WF03 | `workflows/WF03_*.json`, `helpers/validation/reviews.py` |
| 6 | WF04 | `workflows/WF04_*.json`, `workflows/TOOL_*.json` |
| 7 | (docs) | `README.md`, `docs/`, `scripts/backup-restore.sh` |
