#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
URL="${N8N_WEBHOOK_URL:-http://localhost:5678/webhook/invoice-intake}"

for f in INV-1042_clean INV-1043_mismatch INV-1044_missing_fields; do
  echo "=== ${f} ==="
  curl -sS -X POST "$URL" \
    -F "request_id=REQ-${f##*-}" \
    -F "invoice_pdf=@sample-data/invoices/${f}.pdf;type=application/pdf" \
    | python3 -c "
import json,sys
try:
    d=json.load(sys.stdin)
except Exception as e:
    print('non-JSON response:', e); sys.exit(0)
print('status  :', d.get('status'))
print('errors  :', d.get('errors'))
print('warnings:', d.get('warnings'))
print('calc    :', d.get('calculated'))
"
  echo
done
