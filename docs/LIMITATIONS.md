# Limitations

Honest constraints of this portfolio project. None of these is a defect — they are deliberate scope boundaries.

## Data

- **Synthetic only.** All suppliers, POs, invoices, VAT IDs, and totals are fictional. No real invoices, no real PII, no real accounting data.
- **Single currency per PO.** The seed uses EUR for all five POs. A real system needs multi-currency with FX rates.
- **One tax rate (19%).** The demo uses 19% purchase tax. Real systems need per-line tax mapping.

## LLM

- **Groq free tier limits.** `openai/gpt-oss-120b` on the free tier is 30 req/min and 8,000 TPM. The test harness throttles to 20s between asks. A production system would need Dev Tier or a paid provider.
- **Single model.** WF04 uses Groq only. The plan mentions an OpenRouter fallback for WF01 but not for WF04. Adding a Model Selector with two providers is documented as a Phase 8 extension, not part of the current build.
- **English only.** No i18n. Invoice fields are English-only in the schema.

## Infrastructure

- **`postgres:15.7`** is used but **n8n 2.x officially supports PostgreSQL 17+ (16 on compatibility)**. Everything works on 15.7, but n8n prints a deprecation warning. A production deployment should use `postgres:17`.
- **Local Docker only.** The plan requires local persistence for Odoo's filestore. Public free-tier hosting would break filestore persistence — documented as an optional Phase 8 experiment.
- **Single-node.** No horizontal scaling, no Redis queue, no external task runner. Fine for a demo, not for production.

## Odoo

- **Community Edition only.** Some features (bank sync, advanced accounting) are Enterprise-only and not used.
- **Draft bills only.** No bill posting, no payment, no refund, no credit note. All intentionally out of scope.
- **One company, one chart of accounts.** The demo does not exercise multi-company or multi-accounting standards.
- **Integration user is not fully locked down.** It has Purchase/User which allows creating POs. For a real deployment, reduce to read-only on `purchase.order` and `account.move`.

## Validation

- **2-cent tolerance.** Anything beyond 2 cents routes to `NEEDS_REVIEW`. Real systems may accept partial deliveries or price drift — this demo does not.
- **Single line item unit prices must match exactly.** The matcher does not compare line-level items against PO lines; it compares totals only. Line-level matching is a documented Phase 8 extension.
- **OCR not exercised.** All fixtures are text-based PDFs. `PLAN.md` §4 requires Tesseract only after text PDFs work, and that path is documented but not tested here.

## AI Agent

- **Prompt injection defence is best-effort.** The system prompt instructs the model to treat input as data. The structural defence is that no write tool exists. The prompt-injection test passed on Groq's `gpt-oss-120b`, but no guarantee is offered against all future model updates.
- **Tool-call rate limits.** 12 harness asks, 20s apart, complete in ~4 minutes and stay under the 8,000 TPM ceiling. Larger test suites need higher rate limits.
- **The agent does not do arithmetic.** If a user asks "what is 4 × 12.50", the agent will defer to the validator. This is deliberate — LLM arithmetic is unreliable.

## Testing

- **No unit tests in `pytest`.** Validation is exercised through:
  - `scripts/test-wf01.sh` (3 fixtures)
  - `scripts/test-wf04.sh` (12 behaviour cases)
  - Manual DB-level checks after each test run
- **No load testing.** Single-user demo. No concurrency tested.
- **No fuzz testing.** All inputs are hand-authored fixtures.

## What this project is NOT

- Not a production SaaS.
- Not a real accounting system.
- Not compliant with any accounting standard.
- Not audited.
- Not a template to deploy directly — it is a teaching artifact.

## What this project IS

- A working demonstration that AI agents can be safely constrained in a regulated-adjacent domain.
- A reproducible reference for `toolWorkflow` wiring on n8n 2.42.4.
- A concrete example of the "LLM extracts, code validates, human approves" pattern.
- A portfolio piece showing end-to-end ownership: infrastructure, integration, security, testing, and documentation.
