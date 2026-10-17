# Start the app locally on Windows with one command:  powershell -File app\testme.ps1
# Uses uv when available (no global installs needed), otherwise the current python.
$ErrorActionPreference = 'Stop'
Set-Location $PSScriptRoot
$port = if ($env:PORT) { $env:PORT } else { '8000' }
Write-Host "Bikeshare Fleet Quality Control -> http://127.0.0.1:$port/"
if (Get-Command uv -ErrorAction SilentlyContinue) {
    uv run --no-project --python 3.12 --with-requirements requirements.txt python -m uvicorn app:app --host 127.0.0.1 --port $port
} else {
    python -m pip install -r requirements.txt
    python -m uvicorn app:app --host 127.0.0.1 --port $port
}
