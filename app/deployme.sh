#!/usr/bin/env bash
# Publish exactly the files listed in the committed manifest.json.
# Needs CONNECT_SERVER and CONNECT_API_KEY in the environment or a gitignored app/.env.
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")"
if [[ -f .env ]]; then
  set -a; source .env; set +a
fi
: "${CONNECT_SERVER:?Set CONNECT_SERVER (in app/.env or the environment)}"
: "${CONNECT_API_KEY:?Set CONNECT_API_KEY (in app/.env or the environment)}"
python -m pip install --quiet rsconnect-python
rsconnect deploy manifest manifest.json \
  --server "$CONNECT_SERVER" --api-key "$CONNECT_API_KEY" \
  --title "Bikeshare Fleet Quality Control"
