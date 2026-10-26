#!/usr/bin/env bash
set -euo pipefail
docker exec -u node northstar-n8n n8n "$@"
