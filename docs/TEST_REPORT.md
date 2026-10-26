# Test Report

> Record **actual** outcomes only. Never claim coverage you did not run.

## Phase 1 — Local foundation

| Test | Command | Expected | Actual | Date |
|------|---------|----------|--------|------|
| Compose parses & interpolates | `docker compose config >/dev/null` | exit 0 | _todo_ | |
| All services running | `docker compose ps` | 3 × `Up` / `healthy` | _todo_ | |
| Odoo responds | `curl -o /dev/null -w "%{http_code}\n" http://localhost:8069/web/database/manager` | `200` | _todo_ | |
| n8n responds | `curl -o /dev/null -w "%{http_code}\n" http://localhost:5678/` | `200` or `30x` | _todo_ | |
| PostgreSQL roles persisted | `docker compose exec postgres psql -U postgres -c "\du"` | shows `odoo_user`, `n8n_user` | _todo_ | |
| Data survives restart | `docker compose down && docker compose up -d` | n8n owner account still works | _todo_ | |

## Phase 3 — WF01 end-to-end via n8n CLI

| Fixture | Expected | Actual status | Actual errors/warnings | Date |
|---|---|---|---|---|
| INV-1042_clean.pdf | READY_FOR_MATCH, 59.50 | _todo_ | _todo_ | |
| INV-1043_mismatch.pdf | NEEDS_REVIEW, 160.00 vs 148.75 | _todo_ | _todo_ | |
| INV-1044_missing_fields.pdf | NEEDS_REVIEW, missing PO/currency | _todo_ | _todo_ | |

Method: `n8n import:workflow` + `n8n update:workflow --active` + restart;
no editor UI used. Validator is the only source of `calculated`.

## Phase 4 — WF02 final results (EUR relabel via write)

| # | Test | Expected | Actual |
|---|---|---|---|
| 1 | Clean: supplier 7 + PO-204 + EUR + total 113.05 | MATCHED | _todo_ |
| 2 | Unknown supplier DEMO-TAX-999 | NEEDS_REVIEW, "no supplier found" | _todo_ |
| 3 | Missing PO PO-999 | NEEDS_REVIEW, "purchase order not found" | _todo_ |
| 4 | PO-205 belongs to partner 8, not supplier 7 | NEEDS_REVIEW, partner-id mismatch | _todo_ |
| 5 | Supplier auto-creation | Never happens | _todo_ |

Note: POs were originally created under the company default currency (TND).
Relabeled to EUR via write() without altering line totals; verified amounts
unchanged after relabel. EUR currency id = 126.
