# Security

## Threat model

| Threat | Mitigation | Evidence |
|---|---|---|
| LLM hallucinates a supplier / PO / bill ID | Tools return only what Odoo returns. The system prompt forbids invention. The tool endpoints never fabricate. | WF04 test: "Show supplier 99999" → *"No supplier found"* |
| LLM computes wrong totals | Amounts are recalculated with `Decimal` in `validate_invoice.py`. Model-provided totals only flag a warning if they differ. | `docs/TEST_REPORT.md` Phase 3 — mismatch caught at 2-cent tolerance |
| LLM writes to Odoo without approval | The agent has **no tool** that can create `account.move`. Its `prepareDraftVendorBill` tool only inserts a row into `invoice_reviews`. Only WF03 (with human `approve`) can create a bill. | WF04 test: "Create draft" → *review queued*, no bill created |
| LLM posts or pays a bill | No tool exists for `action_post` or payments. Even if the model tried, the tool endpoints have no such methods. | WF04 test: "Post bill" → *"I can't post a bill directly"* |
| LLM deletes a supplier | No delete tool exists. Integration user has no `unlink` permission on `res.partner`. | Phase 2: `OK: partner creation blocked` |
| Prompt injection in invoice text | System prompt treats invoice text as data. Tools receive only structured identifiers. | WF04 test: injection prompt refused |
| Duplicate draft bills | `invoice_reviews.request_id` has a `UNIQUE` constraint. `decide()` short-circuits if `status != 'pending'`. | Phase 5: second approve returns same bill_id |
| Credential leakage in Git | `.env`, `.odoo_api_key` are gitignored. `.env.example` contains only placeholders. Workflow exports contain no secrets. | `git grep -iE 'sk-|gsk_|sk-or-v1-'` returns nothing |
| Unauthorized Odoo access | Integration user has only Purchase/User and Invoicing/Billing groups. It cannot create partners or change settings. | Phase 2: `partner creation blocked (4)` |

## What the AI Agent can do

| Capability | Allowed | Evidence |
|---|---|---|
| Look up a supplier by name/VAT | ✅ | tool `lookupSupplier` → `/tool/lookup_supplier` |
| Look up a PO by name | ✅ | tool `lookupPurchaseOrder` → `/tool/lookup_purchase_order` |
| Check invoice processing status | ✅ | tool `invoiceProcessingStatus` → `/tool/invoice_status` |
| Check a vendor bill state | ✅ | tool `vendorBillStatus` → `/tool/bill_status` |
| Queue a draft for human review | ✅ | tool `prepareDraftVendorBill` → `/tool/prepare_draft` |
| Escalate to human review | ✅ | tool `sendToHumanReview` → `/tool/escalate` |

## What the AI Agent can NOT do

| Capability | Forbidden because |
|---|---|
| Post a bill | No tool exists |
| Pay a bill | No tool exists |
| Delete anything | No tool exists |
| Create a supplier | No tool exists; integration user lacks permission |
| Run SQL | No tool exists; no database access from n8n |
| Execute shell commands | No tool exists |
| Call arbitrary URLs | Only the 6 registered tool endpoints are reachable |
| Change accounting settings | Integration user lacks admin groups |
| Reveal secrets | No tool returns secrets; system prompt treats input as data |

## Human approval gate

Every write to `account.move` follows this path:

```
agent queues review
      │
      ▼
invoice_reviews row (status=pending)
      │
      ▼
human calls POST /webhook/wf03 action=decide decision=approve
      │
      ▼
WF03 creates ONE draft account.move
      │
      ▼
invoice_reviews row (status=approved, odoo_bill_id set)
```

There is **no path** for the agent to skip the human step. The only workflow with a create tool is WF03, and WF03 requires `action=decide, decision=approve` from an external HTTP caller.

## Deterministic arithmetic

Every invoice has a `calculated` block produced by `helpers/validation/validate_invoice.py`:

- `Decimal` arithmetic — no floating point
- 2-cent tolerance for grand-total comparison
- Line totals always recomputed from `qty × unit_price`
- Subtotal, tax, and grand total recomputed in code

If the model's stated total differs by more than 2 cents, the invoice routes to `NEEDS_REVIEW`. The model's number is never used downstream.

## Audit trail

`invoice_reviews` stores:

- `review_id` — unique identifier
- `request_id` — idempotency key (UNIQUE)
- `invoice` — full normalized JSON
- `match_result` — supplier/PO match outcome
- `status` — pending / approved / rejected
- `reviewer` — who approved/rejected
- `reason` — why
- `odoo_bill_id`, `odoo_bill_name` — the created bill (if any)
- `created_at`, `decided_at` — timestamps

Every decision is recoverable. Every bill is traceable back to its review and its invoice.

## Recommendations for a real deployment

If you adapt this for real use (out of scope for the portfolio):

1. **Increase integration user restrictions** — remove Purchase/User, add a narrower read-only group.
2. **Add SSO to the review webhook** — the current `POST /webhook/wf03` accepts any caller. Wrap it with header auth or OAuth.
3. **Add rate limits** to the validator's `/tool/*` endpoints.
4. **Rotate `N8N_ENCRYPTION_KEY`** regularly.
5. **Log n8n executions to an external SIEM** for full audit.
6. **Use HTTPS** for all endpoints — the current setup is HTTP on localhost only.
7. **Run Postgres 17** — n8n 2.x officially supports it (current setup uses 15.7 for convenience).
