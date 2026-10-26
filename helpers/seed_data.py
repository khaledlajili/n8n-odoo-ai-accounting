#!/usr/bin/env python3
"""
Seed synthetic data for Northstar Trading.
Run: python3 helpers/seed_data.py
"""
import os
import xmlrpc.client

URL = os.environ.get("ODOO_URL", "http://localhost:8069")
DB = os.environ.get("ODOO_DB", "northstar")
USER = os.environ.get("ODOO_USER", "admin@northstar.local")
PASSWORD = os.environ.get("ODOO_PASSWORD", "CHANGE_ME")

common = xmlrpc.client.ServerProxy(f"{URL}/xmlrpc/2/common")
uid = common.authenticate(DB, USER, PASSWORD, {})
if not uid:
    raise SystemExit("Authentication failed. Check ODOO_USER / ODOO_PASSWORD.")

models = xmlrpc.client.ServerProxy(f"{URL}/xmlrpc/2/object")

def call(model, method, *args, **kwargs):
    return models.execute_kw(DB, uid, PASSWORD, model, method, list(args), kwargs)

# --- Company ---
company = call("res.company", "search_read", [], fields=["id", "name"], limit=1)[0]
print(f"Company: {company['name']} (id={company['id']})")

# Resolve EUR so POs are created in the fixture currency
eur_hits = call("res.currency", "search_read", [["name", "=", "EUR"]], fields=["id","active"], limit=1)
if not eur_hits:
    raise SystemExit("EUR not found — enable it in Accounting settings first")
eur_id = eur_hits[0]["id"]
if not eur_hits[0]["active"]:
    try:
        call("res.currency", "write", [eur_id], {"active": True})
        print(f"Activated EUR (id={eur_id})")
    except Exception as e:
        print(f"WARN: cannot activate EUR as integration user: {e}")

# --- Suppliers ---
suppliers = [
    ("Northstar Office Supplies", "DEMO-TAX-001"),
    ("Alpine Paper GmbH",       "DEMO-TAX-002"),
    ("Baltic Toner OÜ",         "DEMO-TAX-003"),
    ("Cedar Furniture Ltd",     "DEMO-TAX-004"),
    ("Delta Cleaning Services", "DEMO-TAX-005"),
]

supplier_ids = {}
for name, vat in suppliers:
    existing = call("res.partner", "search", [["name", "=", name]], limit=1)
    if existing:
        supplier_ids[name] = existing[0]
        print(f"Supplier exists: {name} (id={existing[0]})")
        continue
    sid = call("res.partner", "create", {
        "name": name,
        "vat": vat,
        "is_company": True,
        "supplier_rank": 1,
        "email": f"billing@{name.lower().replace(' ', '')[:12]}.example",
    })
    supplier_ids[name] = sid
    print(f"Created supplier: {name} (id={sid})")

# --- Products ---
products = [
    ("Printer Paper A4", "PROD-PAPER", 12.50),
    ("Toner Cartridge Black", "PROD-TONER", 45.00),
    ("Office Chair", "PROD-CHAIR", 89.00),
    ("Cleaning Service (hour)", "PROD-CLEAN", 25.00),
    ("Desk Lamp", "PROD-LAMP", 32.00),
]

product_ids = {}
for name, default_code, price in products:
    existing = call("product.product", "search", [["default_code", "=", default_code]], limit=1)
    if existing:
        product_ids[name] = existing[0]
        print(f"Product exists: {name} (id={existing[0]})")
        continue
    pid = call("product.product", "create", {
        "name": name,
        "default_code": default_code,
        "list_price": price,
        "type": "consu",
        "purchase_ok": True,
    })
    product_ids[name] = pid
    print(f"Created product: {name} (id={pid})")

# --- Purchase Orders ---
pos = [
    ("PO-204", "Northstar Office Supplies", [("Printer Paper A4", 4), ("Toner Cartridge Black", 1)]),
    ("PO-205", "Alpine Paper GmbH",         [("Printer Paper A4", 10)]),
    ("PO-206", "Baltic Toner OÜ",           [("Toner Cartridge Black", 3)]),
    ("PO-207", "Cedar Furniture Ltd",        [("Office Chair", 2), ("Desk Lamp", 3)]),
    ("PO-208", "Delta Cleaning Services",    [("Cleaning Service (hour)", 8)]),
]

for po_name, supplier_name, lines in pos:
    existing = call("purchase.order", "search", [["name", "=", po_name]], limit=1)
    if existing:
        print(f"PO exists: {po_name} (id={existing[0]})")
        continue
    line_cmds = []
    for prod_name, qty in lines:
        line_cmds.append((0, 0, {
            "product_id": product_ids[prod_name],
            "product_qty": qty,
            "price_unit": next(p for n, c, p in products if n == prod_name),
        }))
    po_id = call("purchase.order", "create", {
        "name": po_name,
        "partner_id": supplier_ids[supplier_name],
        "currency_id": eur_id,
        "order_line": line_cmds,
    })
    print(f"Created PO: {po_name} (id={po_id})")

print("\nSeed complete.")
