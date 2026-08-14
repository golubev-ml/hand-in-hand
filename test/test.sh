#!/usr/bin/env bash
set -euo pipefail
API_URL="${API_URL:-http://api:8000}"
echo ">>> Ждём API..."
for i in $(seq 1 60); do
  curl -sf "$API_URL/api/pictures" >/dev/null 2>&1 && break
  sleep 1
done
echo ">>> UNIT"
python -m pytest test/unit -q
echo ">>> API"
python -m pytest test/api -q
echo ">>> E2E"
python -m pytest test/e2e -q --ignore-https-errors
echo ">>> ALL TESTS PASSED"
