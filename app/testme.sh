#!/usr/bin/env bash
# Install the pinned dependencies and start the app: bash app/testme.sh
# Uses uv when available (no global installs), otherwise pip into the current python.
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")"
echo "Bikeshare Fleet Quality Control -> http://127.0.0.1:${PORT:-8000}/"
if command -v uv >/dev/null 2>&1; then
  exec uv run --no-project --python 3.12 --with-requirements requirements.txt \
    python -m uvicorn app:app --host 127.0.0.1 --port "${PORT:-8000}"
fi
python -m pip install --quiet -r requirements.txt
exec python -m uvicorn app:app --host 127.0.0.1 --port "${PORT:-8000}"
