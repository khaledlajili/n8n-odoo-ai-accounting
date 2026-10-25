#!/usr/bin/env python3
"""Generate synthetic invoice PDFs for Phase 3 tests."""
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
import os

OUT = "sample-data/invoices"
os.makedirs(OUT, exist_ok=True)

def invoice(path, supplier, tax_id, inv_no, inv_date, due_date, currency,
            po_no, lines, subtotal, tax_total, grand_total):
    c = canvas.Canvas(path, pagesize=A4)
    w, h = A4
    y = h - 60
    c.setFont("Helvetica-Bold", 14)
    c.drawString(40, y, "INVOICE"); y -= 25
    c.setFont("Helvetica", 10)
    for label, value in [
        ("Supplier", supplier), ("Tax ID", tax_id),
        ("Invoice #", inv_no), ("Invoice date", inv_date),
        ("Due date", due_date), ("Currency", currency),
        ("PO reference", po_no),
    ]:
        c.drawString(40, y, f"{label}: {value}"); y -= 16
    y -= 8
    c.setFont("Helvetica-Bold", 10)
    c.drawString(40, y, "Description"); c.drawString(260, y, "Qty")
    c.drawString(310, y, "Unit price"); c.drawString(400, y, "Tax %")
    c.drawString(470, y, "Line total"); y -= 14
    c.setFont("Helvetica", 10)
    for desc, qty, unit, tax, total in lines:
        c.drawString(40, y, desc); c.drawString(260, y, str(qty))
        c.drawString(310, y, f"{unit:.2f}"); c.drawString(400, y, f"{tax:.2f}")
        c.drawString(470, y, f"{total:.2f}"); y -= 14
    y -= 10
    c.setFont("Helvetica-Bold", 10)
    c.drawString(380, y, "Subtotal"); c.drawString(470, y, f"{subtotal:.2f}"); y -= 14
    c.drawString(380, y, "Tax total"); c.drawString(470, y, f"{tax_total:.2f}"); y -= 14
    c.drawString(380, y, "Grand total"); c.drawString(470, y, f"{grand_total:.2f}")
    c.save()
    print("wrote", path)

invoice(f"{OUT}/INV-1042_clean.pdf",
        "Northstar Office Supplies", "DEMO-TAX-001", "INV-1042",
        "2026-10-12", "2026-11-11", "EUR", "PO-204",
        [("Printer paper", 4, 12.50, 19.00, 50.00)],
        subtotal=50.00, tax_total=9.50, grand_total=59.50)

invoice(f"{OUT}/INV-1043_mismatch.pdf",
        "Alpine Paper GmbH", "DEMO-TAX-002", "INV-1043",
        "2026-10-13", "2026-11-12", "EUR", "PO-205",
        [("Printer paper", 10, 12.50, 19.00, 125.00)],
        subtotal=125.00, tax_total=23.75, grand_total=160.00)

invoice(f"{OUT}/INV-1044_missing_fields.pdf",
        "Baltic Toner OU", "DEMO-TAX-003", "INV-1044",
        "2026-10-14", "2026-11-13", "", "",
        [("Toner cartridge", 3, 45.00, 19.00, 135.00)],
        subtotal=135.00, tax_total=25.65, grand_total=160.65)
