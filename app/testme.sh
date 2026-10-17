#!/bin/bash
# testme.sh - start the whole tool locally with one command, no arguments.
#   bash app/testme.sh      then open http://localhost:8000
#
# Prerequisites: Python 3.12 (python3.12, or uv, on PATH) and, for the web page, Node.js 20+.
# Idempotent: it reuses the repo's .venv, installs the pinned app/requirements.txt, builds the
# React page into app/static/ when app/frontend/ exists and npm is available, then starts the
# API and page together on one port (PORT, default 8000).

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_DIR="$(dirname "$SCRIPT_DIR")"
VENV="$REPO_DIR/.venv"
PORT="${PORT:-8000}"

if [ ! -x "$VENV/bin/python" ]; then
  if command -v python3.12 >/dev/null 2>&1; then
    python3.12 -m venv "$VENV"
  elif command -v uv >/dev/null 2>&1; then
    uv venv --python 3.12 "$VENV"
  else
    echo "testme.sh: need Python 3.12 (python3.12 or uv on PATH) to create $VENV" >&2
    exit 1
  fi
fi
PY="$VENV/bin/python"

if ! "$PY" -m pip --version >/dev/null 2>&1; then
  "$PY" -m ensurepip --upgrade >/dev/null 2>&1 || true
fi
if "$PY" -m pip --version >/dev/null 2>&1; then
  "$PY" -m pip install --quiet --disable-pip-version-check -r "$SCRIPT_DIR/requirements.txt"
else
  uv pip install --quiet --python "$PY" -r "$SCRIPT_DIR/requirements.txt"
fi

if [ -f "$SCRIPT_DIR/frontend/package.json" ]; then
  if command -v npm >/dev/null 2>&1; then
    (cd "$SCRIPT_DIR/frontend" && npm ci --no-audit --no-fund --silent && npm run build --silent)
  elif [ -f "$SCRIPT_DIR/static/index.html" ]; then
    echo "testme.sh: npm not found; serving the already-built page in app/static/" >&2
  else
    echo "testme.sh: npm not found and no built page; starting the API only (see /docs)" >&2
  fi
fi

cd "$SCRIPT_DIR"
echo "Bikeshare dispatch tool: http://localhost:${PORT}  (API docs: http://localhost:${PORT}/docs)"
exec "$PY" -m uvicorn app:app --host 0.0.0.0 --port "$PORT"
