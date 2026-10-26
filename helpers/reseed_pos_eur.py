#!/usr/bin/env python3
"""Delete all purchase orders and re-create them in EUR, preserving fixture totals."""
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

# 1. Resolve EUR
eur = call("res.currency", "search_read",
           [["name", "=", "EUR"]],
           fields=["id", "name", "active"], limit=1)
if not eur:
    raise SystemExit("EUR not visible to integration user — check that EUR is active in Odoo")
eur_id = eur[0]["id"]
print(f"EUR id={eur_id} active={eur[0]['active']}")

# 2. Delete existing POs (draft-only; purchase.order.unlink refuses confirmed)
pos = call("purchase.order", "search_read", [], fields=["id", "name", "state"])
drafts = [p["id"] for p in pos if p["state"] in ("draft", "cancel")]
if len(drafts) != len(pos):
    blocked = [p["name"] for p in pos if p["state"] not in ("draft", "cancel")]
    raise SystemExit(f"some POs are not draft/cancel and cannot be deleted: {blocked}")
if drafts:
    call("purchase.order", "unlink", drafts)
    print(f"deleted {len(drafts)} purchase orders")
else:
    print("no POs to delete")

# 3. Re-create in EUR using the same fixture shape as seed_data.py
suppliers = [
    ("Northstar Office Supplies", "DEMO-TAX-001"),
    ("Alpine Paper GmbH",         "DEMO-TAX-002"),
    ("Baltic Toner OÜ",           "DEMO-TAX-003"),
    ("Cedar Furniture Ltd",       "DEMO-TAX-004"),
    ("Delta Cleaning Services",   "DEMO-TAX-005"),
]
products = [
    ("Printer Paper A4",       "PROD-PAPER", 12.50),
    ("Toner Cartridge Black",  "PROD-TONER", 45.00),
    ("Office Chair",           "PROD-CHAIR", 89.00),
    ("Cleaning Service (hour)", "PROD-CLEAN", 25.00),
    ("Desk Lamp",              "PROD-LAMP",  32.00),
]
pos_spec = [
    ("PO-204", "Northstar Office Supplies", [("Printer Paper A4", 4),      ("Toner Cartridge Black", 1)]),
    ("PO-205", "Alpine Paper GmbH",         [("Printer Paper A4", 10)]),
    ("PO-206", "Baltic Toner OÜ",           [("Toner Cartridge Black", 3)]),
    ("PO-207", "Cedar Furniture Ltd",       [("Office Chair", 2), ("Desk Lamp", 3)]),
    ("PO-208", "Delta Cleaning Services",   [("Cleaning Service (hour)", 8)]),
]

supplier_ids = {}
for name, vat in suppliers:
    hits = call("res.partner", "search", [["name", "=", name]], limit=1)
    if not hits:
        raise SystemExit(f"missing supplier {name!r} — re-run seed_data.py")
    supplier_ids[name] = hits[0]

product_ids  = {}
product_price = {}
for name, code, price in products:
    hits = call("product.product", "search", [["default_code", "=", code]], limit=1)
    if not hits:
        raise SystemExit(f"missing product {code!r} — re-run seed_data.py")
    product_ids[name]   = hits[0]
    product_price[name] = price

for po_name, supplier_name, lines in pos_spec:
    line_cmds = [(0, 0, {
        "product_id": product_ids[prod],
        "product_qty": qty,
        "price_unit": product_price[prod],
    }) for prod, qty in lines]
    po_id = call("purchase.order", "create", {
        "name": po_name,
        "partner_id": supplier_ids[supplier_name],
        "currency_id": eur_id,
        "order_line": line_cmds,
    })
    print(f"created {po_name} (id={po_id})")

# 4. Verify
print("\nCurrent POs:")
for po in call("purchase.order", "search_read", [],
               fields=["id", "name", "partner_id", "amount_total", "currency_id", "state"], limit=20):
    partner  = po["partner_id"][1] if po.get("partner_id") else "-"
    currency = po["currency_id"][1] if po.get("currency_id") else "-"
    print(f"  id={po['id']:>2}  {po['name']:<8}  {partner:<30}  {currency}  total={po['amount_total']}  state={po['state']}")
