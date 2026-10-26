#!/usr/bin/env python3
"""
Deterministic supplier + PO matching for WF02.

Input  (stdin):  { "invoice": <validated invoice>, "supplier_candidates": [...], "po_candidates": [...] }
Output (stdout): { "status": "MATCHED"|"NEEDS_REVIEW"|"REJECTED", "match": {...}, "errors": [...], "warnings": [...] }
"""
import json, sys
from decimal import Decimal, ROUND_HALF_UP

TOL = Decimal("0.02")

def q2(d): return d.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

def norm_name(s):
    return " ".join(str(s or "").lower().split())

def norm_vat(s):
    return "".join(str(s or "").upper().split())

def main():
    data = json.load(sys.stdin)
    inv = data["invoice"]
    suppliers = data.get("supplier_candidates", [])
    pos = data.get("po_candidates", [])

    errors, warnings = [], []
    match = {"supplier": None, "purchase_order": None, "currency_ok": None}

    # ---------- Supplier matching ----------
    inv_vat = norm_vat(inv.get("supplier_tax_id"))
    inv_name = norm_name(inv.get("supplier_name"))

    # Strong: VAT exact
    vat_hits = [s for s in suppliers if norm_vat(s.get("vat")) == inv_vat and inv_vat]
    name_hits = [s for s in suppliers if norm_name(s.get("name")) == inv_name]

    if len(vat_hits) == 1:
        match["supplier"] = vat_hits[0]
        match["supplier_match"] = "vat_exact"
    elif len(vat_hits) > 1:
        errors.append(f"multiple suppliers share VAT {inv.get('supplier_tax_id')}")
    elif len(name_hits) == 1:
        match["supplier"] = name_hits[0]
        match["supplier_match"] = "name_exact"
        warnings.append("matched by name only — VAT missing or unknown")
    elif len(name_hits) > 1:
        errors.append(f"multiple suppliers match name {inv.get('supplier_name')!r}")
    else:
        errors.append(f"no supplier found for vat={inv.get('supplier_tax_id')!r} name={inv.get('supplier_name')!r}")

    # ---------- PO matching ----------
    inv_po = str(inv.get("purchase_order_number") or "").strip()
    if not inv_po:
        errors.append("missing purchase_order_number")
    else:
        po_hits = [p for p in pos if str(p.get("name", "")).strip() == inv_po]
        if len(po_hits) == 1:
            match["purchase_order"] = po_hits[0]
        elif len(po_hits) > 1:
            errors.append(f"multiple purchase orders named {inv_po!r}")
        else:
            errors.append(f"purchase order {inv_po!r} not found in Odoo")

    # ---------- Currency ----------
    if match["supplier"] and match["purchase_order"]:
        po_currency = (match["purchase_order"].get("currency_id") or [None, None])[1]
        inv_currency = (inv.get("currency") or "").upper()
        if po_currency and inv_currency and po_currency.upper() != inv_currency:
            errors.append(f"currency mismatch: invoice {inv_currency}, PO {po_currency}")
            match["currency_ok"] = False
        else:
            match["currency_ok"] = True

    # ---------- PO supplier consistency ----------
    if match["supplier"] and match["purchase_order"]:
        po_partner_id = (match["purchase_order"].get("partner_id") or [None])[0]
        if po_partner_id and po_partner_id != match["supplier"].get("id"):
            errors.append(
                f"PO {match['purchase_order'].get('name')} belongs to partner id "
                f"{po_partner_id}, not matched supplier id {match['supplier'].get('id')}"
            )

    # ---------- Totals (compare invoice calculated vs PO amount_total) ----------
    calc = inv.get("calculated") or {}
    inv_total = calc.get("grand_total")
    po_total = None
    if match["purchase_order"]:
        po_total = match["purchase_order"].get("amount_total")
    if inv_total is not None and po_total is not None:
        if abs(q2(Decimal(str(inv_total))) - q2(Decimal(str(po_total)))) > TOL:
            warnings.append(
                f"invoice grand_total {inv_total} differs from PO amount_total {po_total} "
                f"(beyond {TOL}) — may be partial delivery or price drift"
            )

    # ---------- Final status ----------
    if errors:
        status = "NEEDS_REVIEW"
    elif warnings:
        status = "NEEDS_REVIEW"
    else:
        status = "MATCHED"

    print(json.dumps({
        "status": status,
        "match": {
            "supplier_id": (match["supplier"] or {}).get("id"),
            "supplier_name": (match["supplier"] or {}).get("name"),
            "supplier_match": match.get("supplier_match"),
            "po_id": (match["purchase_order"] or {}).get("id"),
            "po_name": (match["purchase_order"] or {}).get("name"),
            "currency_ok": match.get("currency_ok"),
        },
        "errors": errors,
        "warnings": warnings,
    }, default=str))

if __name__ == "__main__":
    main()
