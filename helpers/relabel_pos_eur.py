#!/usr/bin/env python3
"""Set every draft PO's currency_id to EUR via write().

Odoo 17 line totals (price_subtotal / price_total) are computed from
qty * price_unit + taxes. currency_id is a label on the document;
writing it does NOT convert amounts, which is exactly what we want
for synthetic fixtures where the numbers must stay fixed.
"""
import os, xmlrpc.client, sys

URL  = os.environ.get("ODOO_URL", "http://localhost:8069")
DB   = os.environ.get("ODOO_DB", "northstar")
USER = os.environ.get("ODOO_USER", "n8n@northstar.local")
KEY  = os.environ.get("ODOO_API_KEY", "")
if not KEY:
    raise SystemExit("set ODOO_API_KEY")

common = xmlrpc.client.ServerProxy(f"{URL}/xmlrpc/2/common")
uid = common.authenticate(DB, USER, KEY, {})
if not uid:
    raise SystemExit("auth failed as %s" % USER)

models = xmlrpc.client.ServerProxy(f"{URL}/xmlrpc/2/object")
def call(model, method, *args, **kwargs):
    return models.execute_kw(DB, uid, KEY, model, method, list(args), kwargs)

eur = call("res.currency", "search_read", [["name", "=", "EUR"]],
           fields=["id", "active"], limit=1)
if not eur:
    raise SystemExit("EUR not visible to integration user")
eur_id = eur[0]["id"]
print(f"EUR id={eur_id} active={eur[0]['active']}")

# Snapshot before
before = call("purchase.order", "search_read", [],
              fields=["id", "name", "currency_id", "amount_total", "state"])
print("\nBefore:")
for p in before:
    print(f"  id={p['id']:>2}  {p['name']:<8}  {p['currency_id'][1]:<4}  total={p['amount_total']}  state={p['state']}")

# Only touch those not already EUR
to_fix = [p["id"] for p in before if p["currency_id"][0] != eur_id]
if not to_fix:
    print("\nAll POs already in EUR — nothing to do.")
else:
    try:
        call("purchase.order", "write", to_fix, {"currency_id": eur_id})
        print(f"\nWrote currency_id=EUR to {len(to_fix)} POs")
    except xmlrpc.client.Fault as e:
        print(f"\nWRITE FAILED: {e.faultString}", file=sys.stderr)
        print("If the message mentions 'access' or 'permission', the integration user", file=sys.stderr)
        print("lacks write rights on purchase.order. In that case run this script as", file=sys.stderr)
        print("admin (paste admin@northstar.local + password at the prompt).", file=sys.stderr)
        raise

# Verify
after = call("purchase.order", "search_read", [],
             fields=["id", "name", "partner_id", "amount_total", "currency_id", "state"])
print("\nAfter:")
for p in after:
    partner = p["partner_id"][1] if p.get("partner_id") else "-"
    print(f"  id={p['id']:>2}  {p['name']:<8}  {partner:<30}  {p['currency_id'][1]:<4}  total={p['amount_total']}  state={p['state']}")

# Sanity: totals unchanged vs before?
before_totals = {p["id"]: p["amount_total"] for p in before}
changed = [(p["name"], before_totals.get(p["id"]), p["amount_total"])
           for p in after if p["id"] in before_totals and before_totals[p["id"]] != p["amount_total"]]
if changed:
    print("\nWARNING: amount_total changed during relabel — inspect:", changed)
    sys.exit(1)
print("\nOK: all amounts unchanged after relabel.")
