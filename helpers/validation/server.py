from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
import subprocess, json, sys

import odoo_proxy
import reviews

app = FastAPI()

def _run_script(path, payload):
    proc = subprocess.run([sys.executable, path], input=json.dumps(payload),
                          text=True, capture_output=True, check=False)
    if proc.returncode != 0:
        return JSONResponse({"status": "ERROR", "stderr": proc.stderr})
    return JSONResponse(json.loads(proc.stdout))

@app.post("/validate")
async def validate(req: Request):
    return _run_script("/app/validate_invoice.py", await req.json())

@app.post("/match")
async def match(req: Request):
    return _run_script("/app/match_invoice.py", await req.json())

# ---------- Odoo proxy ----------
@app.post("/odoo/search_read")
async def odoo_search_read(req: Request):
    try: return JSONResponse(odoo_proxy.search_read(await req.json()))
    except Exception as e: return JSONResponse({"error": str(e)})

@app.post("/odoo/search")
async def odoo_search(req: Request):
    try: return JSONResponse(odoo_proxy.search(await req.json()))
    except Exception as e: return JSONResponse({"error": str(e)})

@app.post("/odoo/create")
async def odoo_create(req: Request):
    try: return JSONResponse(odoo_proxy.create(await req.json()))
    except Exception as e: return JSONResponse({"error": str(e)})

@app.post("/odoo/read")
async def odoo_read(req: Request):
    try: return JSONResponse(odoo_proxy.read(await req.json()))
    except Exception as e: return JSONResponse({"error": str(e)})

@app.post("/odoo/po_with_lines")
async def odoo_po_with_lines(req: Request):
    try: return JSONResponse(odoo_proxy.po_with_lines(await req.json()))
    except Exception as e: return JSONResponse({"error": str(e)})

# ---------- review state ----------
@app.post("/review/prepare")
async def review_prepare(req: Request):
    try: return JSONResponse(reviews.prepare(await req.json()))
    except Exception as e: return JSONResponse({"error": str(e)})

@app.post("/review/decide")
async def review_decide(req: Request):
    try: return JSONResponse(reviews.decide(await req.json()))
    except Exception as e: return JSONResponse({"error": str(e)})

@app.post("/review/get")
async def review_get(req: Request):
    try:
        p = await req.json()
        r = reviews.get(p.get("review_id")) if p.get("review_id") else reviews.find_by_request(p.get("request_id"))
        return JSONResponse(r or {"error": "not found"})
    except Exception as e: return JSONResponse({"error": str(e)})

@app.post("/review/find")
async def review_find(req: Request):
    try:
        p = await req.json()
        r = None
        if p.get("review_id"): r = reviews.get(p["review_id"])
        elif p.get("request_id"): r = reviews.find_by_request(p["request_id"])
        elif p.get("invoice_number"): r = reviews.find_by_invoice_number(p["invoice_number"])
        return JSONResponse(r or {"error": "not found"})
    except Exception as e: return JSONResponse({"error": str(e)})

@app.post("/review/prepare_from_request")
async def review_prepare_from_request(req: Request):
    try:
        p = await req.json() if req.headers.get("content-length") not in (None, "0") else {}
        rid = (p or {}).get("request_id") if isinstance(p, dict) else None
        if not rid:
            return JSONResponse({"error": "request_id is required",
                                 "hint": "Ask the user for the request_id, or look it up by invoice number."})
        return JSONResponse(reviews.prepare_from_request(rid))
    except Exception as e: return JSONResponse({"error": str(e)})

# ---------- flat tool endpoints for AI Agent (toolHttpRequest) ----------
def _q(p, k):
    v = (p or {}).get(k)
    return v.strip() if isinstance(v, str) else ""

@app.post("/tool/lookup_supplier")
async def tool_lookup_supplier(req: Request):
    try:
        p = await req.json()
        q = _q(p, "query")
        if not q:
            return JSONResponse({"result": [], "note": "empty query"})
        return JSONResponse(odoo_proxy.search_read({
            "model": "res.partner",
            "domain": [["supplier_rank", ">", 0], "|", ["vat", "=", q], ["name", "ilike", q]],
            "fields": ["id", "name", "vat"], "limit": 5,
        }))
    except Exception as e: return JSONResponse({"error": str(e)})

@app.post("/tool/lookup_purchase_order")
async def tool_lookup_purchase_order(req: Request):
    try:
        p = await req.json()
        name = _q(p, "po_name") or _q(p, "query")
        if not name:
            return JSONResponse({"error": "po_name is required"})
        return JSONResponse(odoo_proxy.po_with_lines({"name": name}))
    except Exception as e: return JSONResponse({"error": str(e)})

@app.post("/tool/invoice_status")
async def tool_invoice_status(req: Request):
    try:
        p = await req.json()
        q = _q(p, "query")
        if not q:
            return JSONResponse({"error": "query is required"})
        r = reviews.find_by_request(q) or reviews.find_by_invoice_number(q)
        if r: return JSONResponse(r)
        return JSONResponse({"error": "not found", "query": q,
                             "hint": "Invoice not processed, or identifier is wrong."})
    except Exception as e: return JSONResponse({"error": str(e)})

@app.post("/tool/bill_status")
async def tool_bill_status(req: Request):
    try:
        p = await req.json()
        q = _q(p, "lookup")
        if not q:
            return JSONResponse({"error": "lookup is required"})
        return JSONResponse(odoo_proxy.search_read({
            "model": "account.move",
            "domain": [["move_type", "=", "in_invoice"], "|", ["name", "=", q], ["ref", "=", q]],
            "fields": ["id", "name", "state", "amount_total", "currency_id", "ref"],
            "limit": 5,
        }))
    except Exception as e: return JSONResponse({"error": str(e)})

@app.post("/tool/prepare_draft")
async def tool_prepare_draft(req: Request):
    try:
        p = await req.json()
        rid = _q(p, "request_id")
        if not rid:
            return JSONResponse({"error": "request_id is required",
                                 "hint": "Ask the user for the request_id, or use invoice_status first."})
        return JSONResponse(reviews.prepare_from_request(rid))
    except Exception as e: return JSONResponse({"error": str(e)})

@app.post("/tool/escalate")
async def tool_escalate(req: Request):
    try:
        p = await req.json()
        rid = _q(p, "request_id")
        if not rid:
            return JSONResponse({"error": "request_id is required"})
        return JSONResponse(reviews.prepare_from_request(rid))
    except Exception as e: return JSONResponse({"error": str(e)})
