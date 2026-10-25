from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
import subprocess, json, sys

app = FastAPI()

@app.post("/validate")
async def validate(req: Request):
    payload = await req.json()
    proc = subprocess.run(
        [sys.executable, "/app/validate_invoice.py"],
        input=json.dumps(payload), text=True, capture_output=True, check=False,
    )
    if proc.returncode != 0:
        return JSONResponse({"status": "ERROR", "stderr": proc.stderr}, status_code=500)
    return JSONResponse(json.loads(proc.stdout))
