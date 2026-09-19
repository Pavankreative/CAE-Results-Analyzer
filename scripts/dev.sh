#!/usr/bin/env bash
# Start the backend and the frontend dev server together.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

if [ ! -f "$ROOT/samples/brk-114.json" ]; then
  echo "Generating sample datasets..."
  python3 "$ROOT/scripts/generate_samples.py"
fi

( cd "$ROOT/backend" && python3 -m uvicorn app.main:app --reload --port 8000 ) &
BACKEND=$!
trap 'kill $BACKEND 2>/dev/null || true' EXIT

( cd "$ROOT/frontend" && npm run dev )
