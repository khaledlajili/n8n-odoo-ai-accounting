#!/usr/bin/env python3
"""
Deterministic invoice validation.

Status semantics:
  REJECTED        - payload cannot be parsed at all (JSON/Pydantic structural failure)
  NEEDS_REVIEW    - parses, but missing fields / mismatches / warnings require a human
  READY_FOR_MATCH - parses, no errors, no warnings
"""
import json
import sys
from datetime import datetime
from decimal import Decimal, ROUND_HALF_UP
from typing import List, Optional

from pydantic import BaseModel, Field, field_validator, model_validator

TOLERANCE = Decimal("0.02")
ALLOWED_CURRENCIES = {"EUR", "USD", "GBP"}

def q2(v: Decimal) -> Decimal:
    return v.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

class Line(BaseModel):
    description: str = Field(min_length=1)
    quantity: Decimal = Field(gt=0)
    unit_price: Decimal = Field(ge=0)
    tax_rate: Decimal = Field(ge=0, le=100)
    line_total: Optional[Decimal] = None

    @model_validator(mode="after")
    def check_line_total(self):
        expected = q2(self.quantity * self.unit_price)
        if self.line_total is not None and abs(q2(self.line_total) - expected) > TOLERANCE:
            raise ValueError(f"line_total {self.line_total} != qty*unit {expected}")
        self.line_total = expected   # always set from code, never trust the model
        return self

class Invoice(BaseModel):
    supplier_name: Optional[str] = None
    supplier_tax_id: Optional[str] = None
    invoice_number: Optional[str] = None
    invoice_date: Optional[str] = None
    due_date: Optional[str] = None
    currency: Optional[str] = None
    purchase_order_number: Optional[str] = None
    lines: List[Line] = Field(default_factory=list)
    subtotal: Optional[Decimal] = None
    tax_total: Optional[Decimal] = None
    grand_total: Optional[Decimal] = None

    @field_validator("currency")
    @classmethod
    def normalize_currency(cls, v):
        if v is None or v == "":
            return None
        return v.strip().upper()

def main():
    try:
        payload = json.load(sys.stdin)
    except Exception as exc:
        print(json.dumps({"status": "REJECTED", "errors": [f"invalid JSON: {exc}"]}))
        return

    try:
        inv = Invoice(**payload)
    except Exception as exc:
        # Structural failure inside a line item, bad Decimal, etc.
        print(json.dumps({"status": "REJECTED", "errors": [str(exc)]}))
        return

    errors, warnings = [], []

    # --- Required top-level fields ---
    if not inv.supplier_name:    errors.append("missing supplier_name")
    if not inv.invoice_number:   errors.append("missing invoice_number")
    if not inv.invoice_date:     errors.append("missing invoice_date")
    if not inv.currency:         errors.append("missing currency")
    if inv.grand_total is None:  errors.append("missing grand_total")
    if not inv.lines:            errors.append("no line items")

    # --- Currency allow-list ---
    if inv.currency and inv.currency not in ALLOWED_CURRENCIES:
        errors.append(f"unsupported currency {inv.currency!r}")

    # --- Date format ---
    for fld in ("invoice_date", "due_date"):
        val = getattr(inv, fld)
        if val:
            try:
                datetime.strptime(val, "%Y-%m-%d")
            except Exception:
                errors.append(f"invalid {fld} format: {val!r}")

    # --- Arithmetic (only if we have the ingredients) ---
    calculated = None
    if inv.lines and inv.grand_total is not None:
        subtotal = q2(sum((l.line_total for l in inv.lines), Decimal("0")))
        tax      = q2(sum((l.line_total * l.tax_rate / Decimal("100") for l in inv.lines), Decimal("0")))
        grand    = q2(subtotal + tax)
        if abs(grand - q2(inv.grand_total)) > TOLERANCE:
            errors.append(f"grand_total mismatch: stated {q2(inv.grand_total)}, calculated {grand}")
        calculated = {
            "subtotal":   str(subtotal),
            "tax_total":  str(tax),
            "grand_total": str(grand),
        }

    # --- Soft warnings (data quality) ---
    if not inv.purchase_order_number: warnings.append("missing purchase_order_number")
    if not inv.supplier_tax_id:       warnings.append("missing supplier_tax_id")

    status = "READY_FOR_MATCH" if (not errors and not warnings) else "NEEDS_REVIEW"

    print(json.dumps({
        "status":     status,
        "normalized": inv.model_dump(mode="json"),
        "calculated": calculated,
        "errors":     errors,
        "warnings":   warnings,
    }, default=str))

if __name__ == "__main__":
    main()
