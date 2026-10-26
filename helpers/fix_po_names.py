#!/usr/bin/env python3
"""One-time: rename auto-sequenced POs to match the fixtures."""
import os, xmlrpc.client

URL = os.environ.get("ODOO_URL", "http://localhost:8069")
DB = os.environ.get("ODOO_DB", "northstar")
USER = os.environ.get("ODOO_USER", "n8n@northstar.local")
KEY = os.environ.get("ODOO_API_KEY", "")

if not KEY:
    raise SystemExit("Set ODOO_API_KEY before running")

common = xmlrpc.client.ServerProxy(f"{URL}/xmlrpc/2/common")
uid = common.authenticate(DB, USER, KEY, {})
if not uid:
    raise SystemExit("auth failed")

models = xmlrpc.client.ServerProxy(f"{URL}/xmlrpc/2/object")
def call(model, method, *args, **kwargs):
    return models.execute_kw(DB, uid, KEY, model, method, list(args), kwargs)

# Map current -> desired. We resolve by partner, not by sequence, to be safe.
desired = [
    ("Northstar Office Supplies", "PO-204"),
    ("Alpine Paper GmbH",         "PO-205"),
    ("Baltic Toner OÜ",           "PO-206"),
    ("Cedar Furniture Ltd",       "PO-207"),
    ("Delta Cleaning Services",   "PO-208"),
]

for partner_name, new_name in desired:
    partners = call("res.partner", "search", [["name", "=", partner_name]], limit=1)
    if not partners:
        print(f"  skip: no partner {partner_name!r}"); continue
    partner_id = partners[0]
    pos = call("purchase.order", "search_read",
               [["partner_id", "=", partner_id]],
               fields=["id", "name", "state"], limit=1)
    if not pos:
        print(f"  skip: no PO for {partner_name!r}"); continue
    po = pos[0]
    if po["name"] == new_name:
        print(f"  ok:   {po['name']} already set")
        continue
    call("purchase.order", "write", [po["id"]], {"name": new_name})
    print(f"  renamed id={po['id']}: {po['name']} -> {new_name}")

# Verify
print("\nCurrent POs:")
for po in call("purchase.order", "search_read", [], fields=["id", "name", "partner_id", "amount_total", "state"], limit=10):
    partner = po["partner_id"][1] if po.get("partner_id") else "-"
    print(f"  id={po['id']:>2}  {po['name']:<8}  {partner:<30}  state={po['state']:<8}  total={po['amount_total']}")
