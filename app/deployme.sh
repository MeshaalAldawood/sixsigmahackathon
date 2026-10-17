#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")"
python -m pip install rsconnect-python
if [[ -f .env ]]; then
  # Local publisher settings are gitignored.
  source .env
fi
args=(deploy fastapi --entrypoint app:app)
if [[ -n "${CONNECT_SERVER:-}" ]]; then args+=(--server "$CONNECT_SERVER"); fi
if [[ -n "${CONNECT_API_KEY:-}" ]]; then args+=(--api-key "$CONNECT_API_KEY"); fi
rsconnect "${args[@]}" .
