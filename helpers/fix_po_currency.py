#!/usr/bin/env python3
"""One-time: set all purchase.order rows to EUR so fixtures match."""
import os, xmlrpc.client

URL  = os.environ.get("ODOO_URL", "http://localhost:8069")
DB   = os.environ.get("ODOO_DB", "northstar")
USER = os.environ.get("ODOO_USER", "n8n@northstar.local")
KEY  = os.environ.get("ODOO_API_KEY", "")

if not KEY:
    raise SystemExit("set ODOO_API_KEY")

common = xmlrpc.client.ServerProxy(f"{URL}/xmlrpc/2/common")
uid = common.authenticate(DB, USER, KEY, {})
if not uid:
    raise SystemExit("auth failed")

models = xmlrpc.client.ServerProxy(f"{URL}/xmlrpc/2/object")
def call(model, method, *args, **kwargs):
    return models.execute_kw(DB, uid, KEY, model, method, list(args), kwargs)

# 1. Find EUR (any state)
eur = call("res.currency", "search_read", [["name", "=", "EUR"]], fields=["id","name","active"], limit=1)
if not eur:
    raise SystemExit("EUR currency not found in Odoo — enable it in Accounting settings first")
eur_id = eur[0]["id"]

# 2. Activate EUR if needed (self-service: n8n integration user may not have perms; try anyway)
if not eur[0]["active"]:
    try:
        call("res.currency", "write", [eur_id], {"active": True})
        print(f"activated EUR (id={eur_id})")
    except xmlrpc.client.Fault as e:
        print(f"WARN: cannot activate EUR as integration user ({e.faultString.splitlines()[0]})")
        print("      enable it manually: Accounting -> Configuration -> Currencies -> EUR -> Activate")
else:
    print(f"EUR already active (id={eur_id})")

# 3. Set every PO to EUR, verify totals don't change
print("\nSetting POs to EUR:")
pos = call("purchase.order", "search_read", [], fields=["id","name","currency_id","amount_total"])
for po in pos:
    if po["currency_id"][0] == eur_id:
        print(f"  ok:   {po['name']} already EUR, total={po['amount_total']}")
        continue
    old_total = po["amount_total"]
    call("purchase.order", "write", [po["id"]], {"currency_id": eur_id})
    # read back
    after = call("purchase.order", "read", [po["id"]], fields=["name","currency_id","amount_total"])[0]
    changed = "" if after["amount_total"] == old_total else f"  (total changed {old_total} -> {after['amount_total']})"
    print(f"  set:  {po['name']} -> EUR, total={after['amount_total']}{changed}")

# 4. Verify
print("\nCurrent POs:")
for po in call("purchase.order", "search_read", [], fields=["id","name","partner_id","amount_total","currency_id","state"], limit=20):
    partner  = po["partner_id"][1] if po.get("partner_id") else "-"
    currency = po["currency_id"][1] if po.get("currency_id") else "-"
    print(f"  id={po['id']:>2}  {po['name']:<8}  {partner:<30}  {currency}  total={po['amount_total']}")
