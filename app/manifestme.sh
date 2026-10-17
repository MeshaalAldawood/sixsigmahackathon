#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")"
python -m pip install rsconnect-python
rsconnect write-manifest fastapi . --entrypoint app:app
