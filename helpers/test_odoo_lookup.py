#!/usr/bin/env python3
"""
Read-only integration smoke test for Phase 2.
Run: python3 helpers/test_odoo_lookup.py
"""
import os
import xmlrpc.client

URL = os.environ.get("ODOO_URL", "http://localhost:8069")
DB = os.environ.get("ODOO_DB", "northstar")
USER = os.environ.get("ODOO_USER", "n8n@northstar.local")
SECRET = os.environ.get("ODOO_API_KEY") or os.environ.get("ODOO_PASSWORD")

if not SECRET:
    raise SystemExit("Set ODOO_API_KEY (or ODOO_PASSWORD) before running.")

common = xmlrpc.client.ServerProxy(f"{URL}/xmlrpc/2/common")
uid = common.authenticate(DB, USER, SECRET, {})
if not uid:
    raise SystemExit("FAIL: authentication rejected (bad credentials).")

print(f"OK: authenticated as uid={uid}")

models = xmlrpc.client.ServerProxy(f"{URL}/xmlrpc/2/object")

def call(model, method, *args, **kwargs):
    return models.execute_kw(DB, uid, SECRET, model, method, list(args), kwargs)

# 1) Read-only supplier search
suppliers = call(
    "res.partner",
    "search_read",
    [["supplier_rank", ">", 0]],
    fields=["id", "name", "vat"],
    limit=10,
)
print(f"\nSuppliers found: {len(suppliers)}")
for s in suppliers:
    print(f"  id={s['id']:>3}  vat={s.get('vat') or '-':<15}  {s['name']}")

# 2) Read-only purchase-order search
pos = call(
    "purchase.order",
    "search_read",
    [],
    fields=["id", "name", "partner_id", "state", "amount_total"],
    limit=10,
)
print(f"\nPurchase orders found: {len(pos)}")
for po in pos:
    partner = po["partner_id"][1] if po.get("partner_id") else "-"
    print(f"  {po['name']:<8}  {partner:<30}  state={po['state']:<10}  total={po['amount_total']}")

# 3) Prove a write is NOT expected to succeed from this script
try:
    call("res.partner", "create", {"name": "SHOULD-NOT-EXIST"})
    print("\nWARNING: integration user was able to create a partner. Tighten permissions.")
except xmlrpc.client.Fault as e:
    print(f"\nOK: partner creation blocked ({e.faultCode}).")

print("\nSmoke test complete.")
