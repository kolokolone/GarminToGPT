param(
  [switch]$SkipApi = $false
)
$ErrorActionPreference = "Stop"
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$Root = Split-Path -Parent $PSScriptRoot

uv run ruff check backend
uv run pytest
npm --prefix (Join-Path $Root "frontend") install
npm --prefix (Join-Path $Root "frontend") run typecheck
npm --prefix (Join-Path $Root "frontend") test
npm --prefix (Join-Path $Root "frontend") run build

if (-not $SkipApi) {
  Write-Host "`n=== Validation API (nécessite backend en cours d'exécution) ===" -ForegroundColor Cyan
  & (Join-Path $PSScriptRoot "test-cloudflare-fresh-url.ps1")
}
