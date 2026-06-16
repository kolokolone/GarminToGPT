param()
$ErrorActionPreference = "Stop"
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$Root = Split-Path -Parent $PSScriptRoot

uv run ruff check backend
uv run pytest
npm --prefix (Join-Path $Root "frontend") install
npm --prefix (Join-Path $Root "frontend") run typecheck
npm --prefix (Join-Path $Root "frontend") test
npm --prefix (Join-Path $Root "frontend") run build
