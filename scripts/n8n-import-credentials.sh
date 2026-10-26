#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."

set -a; source .env; set +a
: "${GROQ_API_KEY:?GROQ_API_KEY missing in .env}"
: "${OPENROUTER_API_KEY:?OPENROUTER_API_KEY missing in .env}"

python3 - <<'PY' > /tmp/n8n-credentials.json
import json, os
print(json.dumps([
  {"id": "groq-cred", "name": "Groq account", "type": "groqApi",
   "data": {"apiKey": os.environ["GROQ_API_KEY"]}},
  {"id": "openrouter-cred", "name": "OpenRouter account", "type": "openRouterApi",
   "data": {"apiKey": os.environ["OPENROUTER_API_KEY"]}},
], indent=2))
PY
chmod 600 /tmp/n8n-credentials.json

docker cp /tmp/n8n-credentials.json northstar-n8n:/home/node/n8n-credentials.json
docker exec -u root northstar-n8n chmod 644 /home/node/n8n-credentials.json
docker exec -u node northstar-n8n n8n import:credentials --input=/home/node/n8n-credentials.json

rm -f /tmp/n8n-credentials.json
docker exec -u root northstar-n8n rm -f /home/node/n8n-credentials.json
echo "Credentials imported."
