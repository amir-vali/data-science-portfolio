# Run FastAPI locally
# Usage: .\scripts\run_api.ps1

$ErrorActionPreference = "Stop"

# Always run from project root
Set-Location (Split-Path -Parent $PSScriptRoot)

# Activate venv if it exists (optional)
if (Test-Path ".venv\Scripts\Activate.ps1") {
    . .venv\Scripts\Activate.ps1
}

Write-Host "Starting API at http://127.0.0.1:8000 ..."
uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
