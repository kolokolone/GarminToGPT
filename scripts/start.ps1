param()
$ErrorActionPreference = "Stop"
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$Root = Split-Path -Parent $PSScriptRoot
$Runtime = Join-Path $Root "runtime"
New-Item -ItemType Directory -Force -Path $Runtime | Out-Null

if (-not (Test-Path -LiteralPath (Join-Path $Root "frontend\out"))) {
    npm --prefix (Join-Path $Root "frontend") install
    npm --prefix (Join-Path $Root "frontend") run build
}

$Backend = Start-Process -FilePath "uv" -ArgumentList @("run", "uvicorn", "app.main:app", "--app-dir", "backend", "--host", "127.0.0.1", "--port", "8000") -WorkingDirectory $Root -PassThru
Set-Content -LiteralPath (Join-Path $Runtime "backend.pid") -Value $Backend.Id -Encoding UTF8
"GarminToGPT lancé: http://127.0.0.1:8000"
