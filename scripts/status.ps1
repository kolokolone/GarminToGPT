param()
$ErrorActionPreference = "Stop"
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

try {
    Invoke-RestMethod -Method Get -Uri "http://127.0.0.1:8000/api/status" -TimeoutSec 5 | ConvertTo-Json -Depth 8
} catch {
    "Backend GarminToGPT indisponible sur http://127.0.0.1:8000"
}
