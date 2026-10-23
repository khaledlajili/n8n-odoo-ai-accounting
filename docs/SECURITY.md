# Security

- No secrets in Git. `.env` is gitignored; `.env.example` contains placeholders only.
- Odoo and n8n use **separate PostgreSQL roles**; each has only the privileges it needs.
- Odoo integration user will be created with **minimum required permissions** in Phase 2.
- Only **synthetic** data. No real invoices or personal data anywhere.
- Every vendor bill requires **explicit human approval** before creation (Phase 5).
- Agent gets only a **narrow, explicit tool set**. No arbitrary SQL, shell, or HTTP.
- Invoice text is treated as **untrusted content**, never as instructions.
- Public demo (Phase 8) is **optional**; must pass the persistence/acceptance checklist in `PLAN.md` §10.

See `PLAN.md` §11 for the full security model.
