$ErrorActionPreference = "Continue"
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

$Target = "http://127.0.0.1:8080/mcp"
$Pass = 0
$Fail = 0

function Test-Step($Name, $Payload, $ExpectSession) {
    param(
        [Parameter(Mandatory)] [string] $Name,
        [Parameter(Mandatory)] [hashtable] $Payload,
        [switch] $ExpectSession
    )
    $Global:Pass = $Pass
    $Global:Fail = $Fail
    try {
        $Body = $Payload | ConvertTo-Json -Depth 5 -Compress
        $Response = Invoke-RestMethod -Method Post -Uri $Target -Body $Body -ContentType "application/json" -TimeoutSec 10 -ErrorAction Stop
        if ($ExpectSession -and -not $Response.'Mcp-Session-Id') {
            Write-Host "  [FAIL] $Name – session manquante" -ForegroundColor Red
            $script:Fail++
        } elseif ($Response.error) {
            Write-Host "  [FAIL] $Name – JSON-RPC error: $($Response.error.message)" -ForegroundColor Red
            $script:Fail++
        } else {
            Write-Host "  [PASS] $Name" -ForegroundColor Green
            $script:Pass++
        }
        return $Response
    } catch {
        Write-Host "  [FAIL] $Name – $($_.Exception.Message)" -ForegroundColor Red
        $script:Fail++
        return $null
    }
}

Write-Host "===========================================" -ForegroundColor Cyan
Write-Host "  MCP Streamable HTTP Probe (PowerShell)" -ForegroundColor Cyan
Write-Host "  Target: $Target" -ForegroundColor Cyan
Write-Host "===========================================" -ForegroundColor Cyan
Write-Host ""

# Step 1: Initialize
Write-Host "[1/3] initialize" -ForegroundColor Yellow
$InitPayload = @{
    jsonrpc = "2.0"
    id      = 1
    method  = "initialize"
    params  = @{
        protocolVersion = "2025-11-25"
        capabilities    = @{}
        clientInfo      = @{
            name    = "mcp-probe-test"
            version = "0.1.0"
        }
    }
}
$InitResult = Test-Step -Name "initialize" -Payload $InitPayload -ExpectSession
if (-not $InitResult -or $InitResult.error) {
    Write-Host ""
    Write-Host "Probe échoué à l'étape initialize – arrêt." -ForegroundColor Red
    exit 1
}

# Extract session ID from headers (PowerShell doesn't expose headers easily via Invoke-RestMethod)
# The session ID is in the Mcp-Session-Id header. We'll use a workaround.
$SessionId = $null
try {
    $WebResponse = Invoke-WebRequest -Method Post -Uri $Target -Body ($InitPayload | ConvertTo-Json -Depth 5 -Compress) -ContentType "application/json" -TimeoutSec 10
    $SessionId = $WebResponse.Headers["Mcp-Session-Id"]
} catch {
    # already tested above, ignore
}

# Step 2: notifications/initialized
Write-Host "[2/3] notifications/initialized" -ForegroundColor Yellow
$NotifPayload = @{
    jsonrpc = "2.0"
    method  = "notifications/initialized"
}
$NotifHeaders = @{
    "Content-Type" = "application/json"
}
if ($SessionId) {
    $NotifHeaders["Mcp-Session-Id"] = $SessionId
}
try {
    $NotifBody = $NotifPayload | ConvertTo-Json -Depth 5 -Compress
    $NotifResponse = Invoke-WebRequest -Method Post -Uri $Target -Body $NotifBody -Headers $NotifHeaders -TimeoutSec 10 -ErrorAction Stop
    if ($NotifResponse.StatusCode -eq 200 -or $NotifResponse.StatusCode -eq 202) {
        Write-Host "  [PASS] notifications/initialized (HTTP $($NotifResponse.StatusCode))" -ForegroundColor Green
        $Pass++
    } else {
        Write-Host "  [FAIL] notifications/initialized – HTTP $($NotifResponse.StatusCode)" -ForegroundColor Red
        $Fail++
    }
} catch {
    Write-Host "  [FAIL] notifications/initialized – $($_.Exception.Message)" -ForegroundColor Red
    $Fail++
}

# Step 3: tools/list
Write-Host "[3/3] tools/list" -ForegroundColor Yellow
$ToolsPayload = @{
    jsonrpc = "2.0"
    id      = 2
    method  = "tools/list"
    params  = @{}
}
try {
    $ToolsBody = $ToolsPayload | ConvertTo-Json -Depth 5 -Compress
    $ToolsResponse = Invoke-RestMethod -Method Post -Uri $Target -Body $ToolsBody -ContentType "application/json" -TimeoutSec 10 -ErrorAction Stop
    if ($ToolsResponse.error) {
        Write-Host "  [FAIL] tools/list – JSON-RPC error: $($ToolsResponse.error.message)" -ForegroundColor Red
        $Fail++
    } elseif ($ToolsResponse.result.tools) {
        $Count = @($ToolsResponse.result.tools).Count
        Write-Host "  [PASS] tools/list – $Count outil(s) trouvé(s)" -ForegroundColor Green
        $Pass++
        # Afficher la liste
        foreach ($Tool in $ToolsResponse.result.tools) {
            Write-Host "         - $($Tool.name)" -ForegroundColor Gray
        }
    } else {
        Write-Host "  [FAIL] tools/list – aucune propriété 'tools' dans la réponse" -ForegroundColor Red
        $Fail++
    }
} catch {
    Write-Host "  [FAIL] tools/list – $($_.Exception.Message)" -ForegroundColor Red
    $Fail++
}

Write-Host ""
Write-Host "===========================================" -ForegroundColor Cyan
Write-Host "  Résultat: $Pass passé(s), $Fail échec(s)" -ForegroundColor Cyan
Write-Host "===========================================" -ForegroundColor Cyan

if ($Fail -gt 0) {
    exit 1
}