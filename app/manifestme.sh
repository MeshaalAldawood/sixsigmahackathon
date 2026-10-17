#!/usr/bin/env bash
# Rebuild the React bundle, refresh the bundled CSVs, and write manifest.json.
# Run on a developer machine (never in CI), then commit manifest.json.
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")"
npm --prefix frontend ci
npm --prefix frontend run build
mkdir -p data
cp ../data/stable.csv ../data/planted_events.csv ../data/edge_case.csv data/
python -m pip install --quiet rsconnect-python
# Called through Python so Windows shells do not expand the exclude globs.
python - <<'EOF'
from rsconnect.main import cli
cli.main(
    args=["write-manifest", "fastapi", ".", "--entrypoint", "app:app", "--overwrite",
          "--exclude", "frontend/**", "--exclude", "__pycache__/**", "--exclude", ".env"],
    prog_name="rsconnect", windows_expand_args=False,
)
EOF
