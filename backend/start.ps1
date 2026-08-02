Set-Location $PSScriptRoot
if (-not (Test-Path .venv)) {
    python -m venv .venv
    .\.venv\Scripts\pip install -r requirements.txt
    .\.venv\Scripts\playwright install chromium
}
.\.venv\Scripts\uvicorn app.main:app --reload --host 0.0.0.0 --port 8000 --log-level debug --access-log
