#!/usr/bin/env python3
"""
Deterministic invoice validation.
Reads a JSON document from stdin, writes a JSON result to stdout.
Never trusts the model's arithmetic.
"""
import json
import sys
from datetime import datetime
from decimal import Decimal, ROUND_HALF_UP
from typing import List, Optional

from pydantic import BaseModel, Field, field_validator, model_validator

TOLERANCE = Decimal("0.02")
ALLOWED_CURRENCIES = {"EUR", "USD", "GBP"}

def D(v) -> Decimal:
    if v is None or v == "":
        return Decimal("0")
    return Decimal(str(v))

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
        self.line_total = expected
        return self

class Invoice(BaseModel):
    supplier_name: str = Field(min_length=1)
    supplier_tax_id: Optional[str] = None
    invoice_number: str = Field(min_length=1)
    invoice_date: str
    due_date: Optional[str] = None
    currency: str
    purchase_order_number: Optional[str] = None
    lines: List[Line] = Field(min_length=1)
    subtotal: Optional[Decimal] = None
    tax_total: Optional[Decimal] = None
    grand_total: Decimal

    @field_validator("currency")
    @classmethod
    def check_currency(cls, v: str) -> str:
        v = v.strip().upper()
        if v not in ALLOWED_CURRENCIES:
            raise ValueError(f"unsupported currency {v!r}")
        return v

    @field_validator("invoice_date", "due_date")
    @classmethod
    def check_date(cls, v: Optional[str]) -> Optional[str]:
        if v in (None, ""):
            return None
        datetime.strptime(v, "%Y-%m-%d")
        return v

    @model_validator(mode="after")
    def recalculate(self):
        subtotal = q2(sum((l.line_total for l in self.lines), Decimal("0")))
        tax = q2(sum((l.line_total * l.tax_rate / Decimal("100") for l in self.lines), Decimal("0")))
        grand = q2(subtotal + tax)
        self.subtotal = subtotal
        self.tax_total = tax
        self._grand_total_expected = grand
        return self

def main():
    payload = json.load(sys.stdin)
    errors, warnings = [], []
    try:
        inv = Invoice(**payload)
    except Exception as exc:
        print(json.dumps({"status": "REJECTED", "errors": [str(exc)]}))
        return

    expected_grand = inv._grand_total_expected
    stated_grand = q2(inv.grand_total)

    if abs(expected_grand - stated_grand) > TOLERANCE:
        errors.append(f"grand_total mismatch: stated {stated_grand}, calculated {expected_grand}")
    if not inv.purchase_order_number:
        warnings.append("missing purchase_order_number")
    if not inv.supplier_tax_id:
        warnings.append("missing supplier_tax_id")

    status = "NEEDS_REVIEW" if (errors or warnings) else "READY_FOR_MATCH"
    print(json.dumps({
        "status": status,
        "normalized": inv.model_dump(mode="json"),
        "calculated": {
            "subtotal": str(inv.subtotal),
            "tax_total": str(inv.tax_total),
            "grand_total": str(expected_grand),
        },
        "errors": errors,
        "warnings": warnings,
    }, default=str))

if __name__ == "__main__":
    main()
