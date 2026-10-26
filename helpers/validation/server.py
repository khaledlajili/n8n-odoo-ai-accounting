from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
import subprocess, json, sys

import odoo_proxy
import reviews

app = FastAPI()

def _run_script(path, payload):
    proc = subprocess.run(
        [sys.executable, path],
        input=json.dumps(payload), text=True, capture_output=True, check=False,
    )
    if proc.returncode != 0:
        return JSONResponse({"status": "ERROR", "stderr": proc.stderr}, status_code=500)
    return JSONResponse(json.loads(proc.stdout))

# --- existing ---
@app.post("/validate")
async def validate(req: Request):
    return _run_script("/app/validate_invoice.py", await req.json())

@app.post("/match")
async def match(req: Request):
    return _run_script("/app/match_invoice.py", await req.json())

# --- Odoo proxy ---
@app.post("/odoo/search_read")
async def odoo_search_read(req: Request):
    try:    return JSONResponse(odoo_proxy.search_read(await req.json()))
    except Exception as e: return JSONResponse({"error": str(e)}, status_code=500)

@app.post("/odoo/search")
async def odoo_search(req: Request):
    try:    return JSONResponse(odoo_proxy.search(await req.json()))
    except Exception as e: return JSONResponse({"error": str(e)}, status_code=500)

@app.post("/odoo/create")
async def odoo_create(req: Request):
    try:    return JSONResponse(odoo_proxy.create(await req.json()))
    except Exception as e: return JSONResponse({"error": str(e)}, status_code=500)

@app.post("/odoo/read")
async def odoo_read(req: Request):
    try:    return JSONResponse(odoo_proxy.read(await req.json()))
    except Exception as e: return JSONResponse({"error": str(e)}, status_code=500)

# --- review state ---
@app.post("/review/prepare")
async def review_prepare(req: Request):
    try:    return JSONResponse(reviews.prepare(await req.json()))
    except Exception as e: return JSONResponse({"error": str(e)}, status_code=500)

@app.post("/review/decide")
async def review_decide(req: Request):
    try:    return JSONResponse(reviews.decide(await req.json()))
    except Exception as e: return JSONResponse({"error": str(e)}, status_code=500)

@app.post("/review/get")
async def review_get(req: Request):
    try:
        payload = await req.json()
        rid = payload.get("review_id")
        r   = reviews.get(rid) if rid else reviews.find_by_request(payload.get("request_id"))
        return JSONResponse(r or {"error": "not found"})
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)
