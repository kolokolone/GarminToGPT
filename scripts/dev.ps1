param()
$ErrorActionPreference = "Stop"
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$Root = Split-Path -Parent $PSScriptRoot
$Runtime = Join-Path $Root "runtime"
New-Item -ItemType Directory -Force -Path $Runtime | Out-Null

function Require-Command($Name) {
    if (-not (Get-Command $Name -ErrorAction SilentlyContinue)) {
        throw "Commande requise introuvable: $Name"
    }
}

Require-Command "uv"
Require-Command "npm"

$Backend = Start-Process -FilePath "uv" -ArgumentList @("run", "uvicorn", "app.main:app", "--app-dir", "backend", "--host", "127.0.0.1", "--port", "8000", "--reload") -WorkingDirectory $Root -PassThru
Set-Content -LiteralPath (Join-Path $Runtime "backend.pid") -Value $Backend.Id -Encoding UTF8

$Frontend = Start-Process -FilePath "npm" -ArgumentList @("--prefix", "frontend", "run", "dev") -WorkingDirectory $Root -PassThru
Set-Content -LiteralPath (Join-Path $Runtime "frontend.pid") -Value $Frontend.Id -Encoding UTF8

"GarminToGPT dev lancé. UI: http://127.0.0.1:3000 API: http://127.0.0.1:8000"
"Arrêt: .\scripts\stop.ps1"
