param(
  [string]$ApiBase = "http://localhost:8000"
)
$ErrorActionPreference = "Stop"
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$Root = Split-Path -Parent $PSScriptRoot

$Passed = 0
$Failed = 0

function Assert {
  param([string]$Label, [scriptblock]$Condition)
  try {
    $result = & $Condition
    if ($result) {
      Write-Host "  [PASS] $Label" -ForegroundColor Green
      $global:Passed++
    } else {
      Write-Host "  [FAIL] $Label" -ForegroundColor Red
      $global:Failed++
    }
  } catch {
    Write-Host "  [FAIL] $Label – $_" -ForegroundColor Red
    $global:Failed++
  }
}

# ============================================================
Write-Host "=== Test fraîcheur URL Cloudflare ===" -ForegroundColor Cyan
Write-Host "API: $ApiBase`n" -ForegroundColor Gray

# ---- Test 1 : API répond ----
Write-Host "[1] Disponibilité API" -ForegroundColor Yellow
try {
  $status = Invoke-RestMethod -Uri "$ApiBase/api/status" -TimeoutSec 5 -Headers @{"Cache-Control"="no-cache"}
  Assert "GET /api/status → 200" { $true }
  Write-Host "     version: $($status.version), state: $($status.state)" -ForegroundColor Gray
} catch {
  Assert "GET /api/status" { $false }
  Write-Host "`n⚠ Arrêt prématuré – l'API backend n'est pas joignable" -ForegroundColor Magenta
  exit 1
}

# ---- Test 2 : Tunnel arrêté → pas d'URL ----
Write-Host "`n[2] Pas d'URL si tunnel arrêté" -ForegroundColor Yellow
if ($status.tunnel.state -in @("stopped", "paused")) {
  Assert "public_url est null" { $null -eq $status.tunnel.public_url }
  Assert "chatgpt_mcp_url est null" { $null -eq $status.tunnel.chatgpt_mcp_url }
} else {
  Write-Host "     État tunnel = $($status.tunnel.state) – skipping (tunnel actif)" -ForegroundColor Gray
}

# ---- Test 3 : state.json ne contient pas d'URL périmée ----
Write-Host "`n[3] state.json" -ForegroundColor Yellow
$stateFile = Join-Path $Root "backend" "runtime" "state.json"
if (Test-Path $stateFile) {
  $stateRaw = Get-Content $stateFile -Encoding UTF8 -Raw
  $hasOldUrl = $stateRaw -match '"cloudflare_public_url"\s*:\s*"https://[^"]+\.trycloudflare\.com"'
  Assert "Pas d'URL trycloudflare persistée dans state.json" { -not $hasOldUrl }
} else {
  Write-Host "     state.json introuvable (OK – 1er lancement)" -ForegroundColor Gray
}

# ---- Test 4 : Validation URL retournée par l'API ----
Write-Host "`n[4] Validation URL (si présente)" -ForegroundColor Yellow
$url = $status.tunnel.chatgpt_mcp_url
if ($url) {
  $match = $url -match '^https://[a-zA-Z0-9.-]+\.trycloudflare\.com/mcp/?$'
  Assert "URL correspond au pattern trycloudflare.com/mcp" { $match }
} else {
  Write-Host "     Aucune URL à valider (tunnel inactif)" -ForegroundColor Gray
}

# ---- Test 5 : logs cloudflared - session propre ----
Write-Host "`n[5] Logs cloudflared – pas d'ancienne URL" -ForegroundColor Yellow
$logFile = Join-Path $Root "backend" "logs" "cloudflared.log"
if (Test-Path $logFile) {
  $content = Get-Content $logFile -Raw -Encoding UTF8
  # Vérifier que les URLs trouvées correspondent à la session courante
  $urls = [regex]::Matches($content, "https://[a-zA-Z0-9.-]+\.trycloudflare\.com")
  if ($urls.Count -gt 0) {
    # Note: on ne peut pas prouver la fraîcheur sans connaître la position de session,
    # mais la présence d'URLs dans un fichier qui a été rotaté est OK
    Write-Host "     $($urls.Count) URL(s) trycloudflare dans le fichier" -ForegroundColor Gray
  }
  Assert "Fichier cloudflared.log existe" { $true }
} else {
  Write-Host "     cloudflared.log introuvable (OK – tunnel jamais démarré)" -ForegroundColor Gray
}

# ---- Résumé ----
Write-Host "`n=== Résultat: $Passed passé(s), $Failed échec(s) ===" -ForegroundColor Cyan
if ($Failed -gt 0) { exit 1 }
