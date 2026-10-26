"""
Minimal XML-RPC proxy to Odoo. Exposes search_read / search / create.
Auth path matches test_odoo_lookup.py (which is known to work).
"""
import os
import xmlrpc.client

ODOO_URL     = os.environ.get("ODOO_INTERNAL_URL", "http://odoo:8069")
ODOO_DB      = os.environ.get("ODOO_DB", "northstar")
ODOO_USER    = os.environ.get("ODOO_USER", "n8n@northstar.local")
ODOO_API_KEY = os.environ.get("ODOO_API_KEY", "")

_uid = {"value": None}

def _client(path):
    return xmlrpc.client.ServerProxy(f"{ODOO_URL}{path}", allow_none=True)

def _authenticate():
    if _uid["value"]:
        return _uid["value"]
    if not ODOO_API_KEY:
        raise RuntimeError("ODOO_API_KEY not set in validator environment")
    common = _client("/xmlrpc/2/common")
    uid = common.authenticate(ODOO_DB, ODOO_USER, ODOO_API_KEY, {})
    if not uid:
        raise RuntimeError("Odoo authentication failed (check ODOO_USER / ODOO_API_KEY)")
    _uid["value"] = uid
    return uid

def _models():
    return _client("/xmlrpc/2/object")

def search_read(payload):
    model  = payload["model"]
    domain = payload.get("domain") or []
    fields = payload.get("fields") or []
    limit  = payload.get("limit")
    kwargs = {"fields": fields}
    if limit:
        kwargs["limit"] = int(limit)
    uid = _authenticate()
    return {"result": _models().execute_kw(
        ODOO_DB, uid, ODOO_API_KEY, model, "search_read", [domain], kwargs)}

def search(payload):
    model  = payload["model"]
    domain = payload.get("domain") or []
    limit  = payload.get("limit")
    kwargs = {}
    if limit:
        kwargs["limit"] = int(limit)
    uid = _authenticate()
    return {"result": _models().execute_kw(
        ODOO_DB, uid, ODOO_API_KEY, model, "search", [domain], kwargs)}

def create(payload):
    """payload = {model, values}  -> {result: <id>}"""
    model  = payload["model"]
    values = payload["values"]
    uid = _authenticate()
    new_id = _models().execute_kw(
        ODOO_DB, uid, ODOO_API_KEY, model, "create", [values])
    return {"result": new_id}

def read(payload):
    """payload = {model, ids, fields}"""
    model  = payload["model"]
    ids    = payload["ids"]
    fields = payload.get("fields") or []
    uid = _authenticate()
    return {"result": _models().execute_kw(
        ODOO_DB, uid, ODOO_API_KEY, model, "read", [ids], {"fields": fields})}
