#!/usr/bin/env bash
# Verify a fresh clone actually works: regenerate the samples, run the backend
# test suite, type-check, test and build the frontend, then smoke-test the API.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

echo "== sample datasets =="
python3 scripts/generate_samples.py

echo "== backend tests =="
( cd backend && python3 -m pytest tests -q )

echo "== frontend =="
if [ -d frontend/node_modules ]; then
  ( cd frontend && npm run typecheck && npm test && npm run build )
else
  echo "frontend/node_modules missing - run 'cd frontend && npm install' to include the frontend"
fi

echo "== API smoke test =="
( cd backend && python3 -m uvicorn app.main:app --port 8765 >/tmp/caer-verify.log 2>&1 ) &
SERVER=$!
trap 'kill $SERVER 2>/dev/null || true' EXIT
for _ in $(seq 1 30); do
  if curl -sf http://127.0.0.1:8765/api/health >/dev/null; then break; fi
  sleep 1
done
curl -sf http://127.0.0.1:8765/api/health
echo
curl -sf http://127.0.0.1:8765/api/simulations/brk-114/fields/von_mises/statistics >/dev/null
echo "API responded correctly."
echo
echo "All checks passed."
