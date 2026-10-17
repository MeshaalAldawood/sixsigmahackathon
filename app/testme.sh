#!/usr/bin/env bash
# Install the pinned dependencies and start the app: bash app/testme.sh
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")"
python -m pip install --quiet -r requirements.txt
echo "Bikeshare Fleet Quality Control -> http://127.0.0.1:${PORT:-8000}/"
python -m uvicorn app:app --host 127.0.0.1 --port "${PORT:-8000}"
