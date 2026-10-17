#!/bin/bash
# deployme.sh - publish app/ to the course Posit Connect server from your machine.
#   bash app/deployme.sh
# Needs CONNECT_SERVER and CONNECT_API_KEY, either exported or in a gitignored .env (repo root or
# app/). They are handed out at the event; never commit them. This targets Posit Connect, not
# Connect Cloud.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_DIR="$(dirname "$SCRIPT_DIR")"
PY="$REPO_DIR/.venv/bin/python"
cd "$SCRIPT_DIR"

for envfile in "$REPO_DIR/.env" "$SCRIPT_DIR/.env"; do
  # shellcheck disable=SC1090
  [ -f "$envfile" ] && set -a && . "$envfile" && set +a
done
if [ -z "${CONNECT_SERVER:-}" ] || [ -z "${CONNECT_API_KEY:-}" ]; then
  echo "deployme.sh: set CONNECT_SERVER and CONNECT_API_KEY (export them or put them in .env)" >&2
  exit 1
fi
for f in data/stable.csv data/planted_events.csv data/edge_case.csv static/index.html manifest.json; do
  [ -f "$f" ] || { echo "deployme.sh: app/$f is missing; see docs/deployment.md" >&2; exit 1; }
done

"$PY" -m pip install --quiet --disable-pip-version-check rsconnect-python 2>/dev/null \
  || uv pip install --quiet --python "$PY" rsconnect-python
"$PY" -m rsconnect.main deploy manifest manifest.json \
  --server "$CONNECT_SERVER" --api-key "$CONNECT_API_KEY" \
  --title "Bikeshare dispatch (Team Six)"
