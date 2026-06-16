param()
$ErrorActionPreference = "Stop"
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$Root = Split-Path -Parent $PSScriptRoot
$Runtime = Join-Path $Root "runtime"

function Stop-RecordedProcess($PidFile) {
    if (-not (Test-Path -LiteralPath $PidFile)) { return }
    $RawPid = Get-Content -LiteralPath $PidFile -ErrorAction SilentlyContinue | Select-Object -First 1
    $ParsedPid = 0
    if (-not [int]::TryParse($RawPid, [ref]$ParsedPid)) { Remove-Item -LiteralPath $PidFile -Force; return }
    $Process = Get-Process -Id $ParsedPid -ErrorAction SilentlyContinue
    if ($Process) {
        Stop-Process -Id $ParsedPid -ErrorAction Stop
        "Processus arrêté: $ParsedPid"
    }
    Remove-Item -LiteralPath $PidFile -Force
}

Stop-RecordedProcess (Join-Path $Runtime "backend.pid")
Stop-RecordedProcess (Join-Path $Runtime "frontend.pid")

try {
    Invoke-RestMethod -Method Post -Uri "http://127.0.0.1:8000/api/mcp/stop" -TimeoutSec 2 | Out-Null
    Invoke-RestMethod -Method Post -Uri "http://127.0.0.1:8000/api/tunnel/stop" -TimeoutSec 2 | Out-Null
} catch {
    "API backend indisponible ou déjà arrêtée."
}

"Arrêt terminé."
