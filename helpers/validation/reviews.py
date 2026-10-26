"""
Review state + idempotency for Phase 5.

Schema (created lazily on first use):
  invoice_reviews(
    review_id TEXT PK,
    request_id TEXT UNIQUE NOT NULL,
    invoice JSONB NOT NULL,
    match_result JSONB NOT NULL,
    status TEXT NOT NULL,       -- 'pending' | 'approved' | 'rejected'
    reviewer TEXT,
    reason TEXT,
    odoo_bill_id INT,
    odoo_bill_name TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    decided_at TIMESTAMPTZ
  )

Idempotency is enforced by the UNIQUE constraint on request_id: any
attempt to create a second bill for the same request_id returns the
already-existing row instead of writing again.
"""
import os
import json
import uuid
import psycopg2
import psycopg2.extras
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
    # FastAPI's JSONResponse cannot serialize datetime; convert to ISO strings
    for k in ("created_at", "decided_at"):
        v = out.get(k)
        if v is not None and hasattr(v, "isoformat"):
            out[k] = v.isoformat()
    return out

# ---------------------------------------------------------------------------
# Prepare
# ---------------------------------------------------------------------------
def prepare(payload):
    """payload = {request_id, invoice, match_result}"""
    _ensure_schema()
    request_id = payload.get("request_id") or f"REQ-{uuid.uuid4().hex[:10]}"
    invoice    = payload.get("invoice") or {}
    match      = payload.get("match_result") or {}

    with _conn() as c, c.cursor() as cur:
        # Idempotency: if request_id already exists, return the existing row
        cur.execute(
            "SELECT * FROM invoice_reviews WHERE request_id = %s",
            (request_id,),
        )
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
        cur.execute(
            "SELECT * FROM invoice_reviews WHERE review_id = %s",
            (review_id,),
        )
        return _row_to_dict(cur.fetchone(), cur)

# ---------------------------------------------------------------------------
# Decide
# ---------------------------------------------------------------------------
def decide(payload):
    """payload = {review_id, decision: 'approve'|'reject', reviewer, reason, odoo_bill:{id,name}|null}"""
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
            # Idempotent: return the already-decided record
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

# ---------------------------------------------------------------------------
# Lookup
# ---------------------------------------------------------------------------
def get(review_id):
    _ensure_schema()
    with _conn() as c, c.cursor() as cur:
        cur.execute("SELECT * FROM invoice_reviews WHERE review_id = %s", (review_id,))
        row = cur.fetchone()
        if not row:
            return None
        return _row_to_dict(row, cur)

def find_by_request(request_id):
    _ensure_schema()
    with _conn() as c, c.cursor() as cur:
        cur.execute("SELECT * FROM invoice_reviews WHERE request_id = %s", (request_id,))
        row = cur.fetchone()
        if not row:
            return None
        return _row_to_dict(row, cur)
