"""
Review state + idempotency for Phase 5 and the AI agent (Phase 6).
"""
import os
import json
import uuid
import psycopg2
from datetime import datetime, timezone

DATABASE_URL = os.environ.get(
    "DATABASE_URL",
    "postgresql://n8n_user:n8n_pass@postgres:5432/n8n_db",
)

CREATE_SQL = """
CREATE TABLE IF NOT EXISTS invoice_reviews (
  review_id       TEXT PRIMARY KEY,
  request_id      TEXT UNIQUE NOT NULL,
  invoice         JSONB NOT NULL,
  match_result    JSONB NOT NULL,
  status          TEXT NOT NULL,
  reviewer        TEXT,
  reason          TEXT,
  odoo_bill_id    INT,
  odoo_bill_name  TEXT,
  created_at      TIMESTAMPTZ DEFAULT NOW(),
  decided_at      TIMESTAMPTZ
);
"""

_ready = {"value": False}

def _conn():
    c = psycopg2.connect(DATABASE_URL)
    c.autocommit = True
    return c

def _ensure_schema():
    if _ready["value"]:
        return
    with _conn() as c, c.cursor() as cur:
        cur.execute(CREATE_SQL)
    _ready["value"] = True

def _row_to_dict(row, cur):
    cols = [d[0] for d in cur.description]
    out = dict(zip(cols, row))
    for k in ("created_at", "decided_at"):
        v = out.get(k)
        if v is not None and hasattr(v, "isoformat"):
            out[k] = v.isoformat()
    return out

# ---------------------------------------------------------------------------
# prepare / decide / get  (Phase 5)
# ---------------------------------------------------------------------------
def prepare(payload):
    _ensure_schema()
    request_id = payload.get("request_id") or f"REQ-{uuid.uuid4().hex[:10]}"
    invoice    = payload.get("invoice") or {}
    match      = payload.get("match_result") or {}

    with _conn() as c, c.cursor() as cur:
        cur.execute("SELECT * FROM invoice_reviews WHERE request_id = %s", (request_id,))
        existing = cur.fetchone()
        if existing:
            return _row_to_dict(existing, cur)

        review_id = f"RV-{uuid.uuid4().hex[:12]}"
        cur.execute(
            """
            INSERT INTO invoice_reviews
              (review_id, request_id, invoice, match_result, status)
            VALUES (%s, %s, %s, %s, 'pending')
            """,
            (review_id, request_id,
             json.dumps(invoice, default=str),
             json.dumps(match, default=str)),
        )
        cur.execute("SELECT * FROM invoice_reviews WHERE review_id = %s", (review_id,))
        return _row_to_dict(cur.fetchone(), cur)

def decide(payload):
    _ensure_schema()
    review_id = payload["review_id"]
    decision  = payload["decision"]
    if decision not in ("approve", "reject"):
        raise ValueError(f"invalid decision {decision!r}")

    with _conn() as c, c.cursor() as cur:
        cur.execute("SELECT * FROM invoice_reviews WHERE review_id = %s", (review_id,))
        row = cur.fetchone()
        if not row:
            raise ValueError(f"review {review_id!r} not found")
        current = _row_to_dict(row, cur)
        if current["status"] != "pending":
            return current

        bill = payload.get("odoo_bill") or {}
        cur.execute(
            """
            UPDATE invoice_reviews
               SET status = %s,
                   reviewer = %s,
                   reason = %s,
                   odoo_bill_id = %s,
                   odoo_bill_name = %s,
                   decided_at = NOW()
             WHERE review_id = %s
            """,
            (
                "approved" if decision == "approve" else "rejected",
                payload.get("reviewer") or "unknown",
                payload.get("reason"),
                bill.get("id"),
                bill.get("name"),
                review_id,
            ),
        )
        cur.execute("SELECT * FROM invoice_reviews WHERE review_id = %s", (review_id,))
        return _row_to_dict(cur.fetchone(), cur)

def get(review_id):
    _ensure_schema()
    with _conn() as c, c.cursor() as cur:
        cur.execute("SELECT * FROM invoice_reviews WHERE review_id = %s", (review_id,))
        row = cur.fetchone()
        return _row_to_dict(row, cur) if row else None

def find_by_request(request_id):
    _ensure_schema()
    with _conn() as c, c.cursor() as cur:
        cur.execute("SELECT * FROM invoice_reviews WHERE request_id = %s", (request_id,))
        row = cur.fetchone()
        return _row_to_dict(row, cur) if row else None

# ---------------------------------------------------------------------------
# Phase 6 additions
# ---------------------------------------------------------------------------
def find_by_invoice_number(invoice_number):
    _ensure_schema()
    with _conn() as c, c.cursor() as cur:
        cur.execute(
            "SELECT * FROM invoice_reviews WHERE invoice->>'invoice_number' = %s",
            (invoice_number,),
        )
        row = cur.fetchone()
        return _row_to_dict(row, cur) if row else None

def prepare_from_request(request_id):
    """Idempotent lookup used by the AI agent's prepare tool."""
    existing = find_by_request(request_id)
    if not existing:
        return {
            "error": "no review found for this request_id",
            "action_required": (
                "Process the invoice through WF01 -> WF02 first. "
                "WF02 auto-creates a pending review on MATCHED."
            ),
        }
    status = existing["status"]
    base = {
        "review_id": existing["review_id"],
        "status": status,
        "request_id": request_id,
        "odoo_bill_id": existing.get("odoo_bill_id"),
        "odoo_bill_name": existing.get("odoo_bill_name"),
    }
    rid = existing["review_id"]
    if status == "approved":
        base["message"] = (
            "This review is already approved and a draft bill exists. "
            "Use get_vendor_bill_status to inspect it. No further action."
        )
    elif status == "rejected":
        base["message"] = "This review was rejected. No bill was created."
    else:
        base["message"] = "Human approval required before any Odoo write."
        base["approve_command"] = (
            f"curl -X POST http://localhost:5678/webhook/wf03 "
            f"-H 'Content-Type: application/json' "
            f"-d '{{\"action\":\"decide\",\"review_id\":\"{rid}\","
            f"\"decision\":\"approve\",\"reviewer\":\"<name>\",\"reason\":\"<why>\"}}'"
        )
        base["reject_command"] = (
            f"curl -X POST http://localhost:5678/webhook/wf03 "
            f"-H 'Content-Type: application/json' "
            f"-d '{{\"action\":\"decide\",\"review_id\":\"{rid}\","
            f"\"decision\":\"reject\",\"reviewer\":\"<name>\",\"reason\":\"<why>\"}}'"
        )
    return base
