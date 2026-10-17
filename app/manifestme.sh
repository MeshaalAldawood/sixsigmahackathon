#!/bin/bash
# manifestme.sh - write app/manifest.json for Posit Connect, on YOUR machine (never in CI).
#   bash app/manifestme.sh
# Run it after app/static/ is built and app/data/ holds the three CSVs, and again after any
# dependency change. It uses the repo's .venv so the manifest records Python 3.12.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PY="$(dirname "$SCRIPT_DIR")/.venv/bin/python"
cd "$SCRIPT_DIR"

"$PY" -m pip install --quiet --disable-pip-version-check rsconnect-python 2>/dev/null \
  || uv pip install --quiet --python "$PY" rsconnect-python
# FastAPI is ASGI, so the mode is `fastapi` (the older `api` mode is WSGI and fails on Connect).
# The React source and build caches are not part of the deployed bundle.
"$PY" -m rsconnect.main write-manifest fastapi . --entrypoint app:app --overwrite \
  --exclude "frontend" --exclude "__pycache__" --exclude "*.pyc"
echo "Done. manifest.json written in: $SCRIPT_DIR"
