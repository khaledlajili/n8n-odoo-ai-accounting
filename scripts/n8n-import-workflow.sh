#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."

FILE="${1:?usage: $0 workflows/WF01_invoice_intake.json}"
[ -f "$FILE" ] || { echo "not found: $FILE"; exit 1; }
NAME=$(basename "$FILE" .json)
REMOTE="/home/node/${NAME}.json"
LOCAL="/tmp/${NAME}.json"

set -a; source .env; set +a
sed -e "s|__GROQ_MODEL__|${GROQ_MODEL:-llama-3.3-70b-versatile}|g" \
    -e "s|__OPENROUTER_MODEL__|${OPENROUTER_MODEL:-meta-llama/llama-3.3-70b-instruct:free}|g" \
    "$FILE" > "$LOCAL"

# n8n 1.70.3 import:workflow expects an ARRAY of workflow objects.
python3 - "$LOCAL" <<'PY'
import json, sys
path = sys.argv[1]
with open(path) as f:
    data = json.load(f)
if isinstance(data, dict) and 'nodes' in data and 'connections' in data:
    data = [data]
elif not isinstance(data, list):
    raise SystemExit("unexpected JSON shape: expected workflow object or array")
with open(path, 'w') as f:
    json.dump(data, f, indent=2)
PY

docker cp "$LOCAL" "northstar-n8n:${REMOTE}"
docker exec -u root northstar-n8n chmod 644 "$REMOTE"
docker exec -u node northstar-n8n n8n import:workflow --input="$REMOTE"
docker exec -u root northstar-n8n rm -f "$REMOTE"

# Resolve workflow ID by exact name (safer than substring matching)
docker exec -u node northstar-n8n n8n export:workflow --all --output=/home/node/all-workflows.json >/dev/null
docker cp northstar-n8n:/home/node/all-workflows.json /tmp/all-workflows.json >/dev/null
WF_ID=$(python3 - "$NAME" <<'PY'
import json, sys
name = sys.argv[1]
with open('/tmp/all-workflows.json') as f:
    ws = json.load(f)
# match by the basename used in the file's "name" field
match = [w for w in ws if w.get('name','') == name]
if not match:
    # fallback: match by the "name" value inside the imported JSON
    with open(f"/tmp/{name}.json") as f:
        payload = json.load(f)
    target = payload[0].get('name', name)
    match = [w for w in ws if w.get('name','') == target]
if not match:
    raise SystemExit(f"workflow '{name}' not found after import")
print(match[0]['id'])
PY
)

docker exec -u node northstar-n8n n8n update:workflow --id="$WF_ID" --active=true
echo "Imported and activated workflow id=${WF_ID}"

rm -f "$LOCAL" /tmp/all-workflows.json
docker exec -u root northstar-n8n rm -f /home/node/all-workflows.json
