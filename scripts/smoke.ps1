# End-to-end smoke on Windows: boot an ephemeral in-memory gateway, provision a real
# account from the FULL cookie jar, mint a key, exercise surfaces.
#
#   $env:CLAUDE_SMOKE_COOKIES='sessionKey=...; cf_clearance=...; __cf_bm=...; _cfuvid=...'
#   $env:CLAUDE_SMOKE_ORG_UUID="<uuid>"; scripts\smoke.ps1
#   # bare sessionKey also works (live calls 403 without cf_clearance):
#   $env:CLAUDE_SMOKE_SESSION_KEY="sk-ant-sid02-..."; scripts\smoke.ps1
#
# Set CLAUDE_SMOKE_USER_AGENT to the browser the cookies came from (default Chrome 148).
# Exit 0 iff every gateway-WIRING check passes; upstream (claude.ai 403/429/5xx) is
# reported but not fatal.
$ErrorActionPreference = "Stop"
Set-Location (Join-Path $PSScriptRoot "..")

$raw = $env:CLAUDE_SMOKE_COOKIES
if (-not $raw -and $env:CLAUDE_SMOKE_SESSION_KEY) { $raw = "sessionKey=$($env:CLAUDE_SMOKE_SESSION_KEY)" }
if (-not $raw) { Write-Error "set CLAUDE_SMOKE_COOKIES (full jar) or CLAUDE_SMOKE_SESSION_KEY"; exit 1 }
$PY = ".venv\Scripts\python.exe"
if (-not (Test-Path $PY)) { Write-Error "venv missing - run scripts\install.bat first"; exit 1 }

$port = if ($env:CLAUDE_SMOKE_PORT) { $env:CLAUDE_SMOKE_PORT } else { "8099" }
$base = "http://127.0.0.1:$port"
$adminToken = & $PY -c "import secrets; print(secrets.token_urlsafe(24))"
$wiringFails = 0

$cookies = @{}
if ($raw -match "=") {
  foreach ($pair in $raw.Split(";")) {
    $p = $pair.Trim(); $i = $p.IndexOf("=")
    if ($i -gt 0) { $cookies[$p.Substring(0, $i).Trim()] = $p.Substring($i + 1).Trim() }
  }
} else { $cookies["sessionKey"] = $raw.Trim() }

$env:CLAUDE_GATEWAY_DB = "memory"
$env:CLAUDE_GATEWAY_ADMIN_TOKEN = $adminToken
$env:CLAUDE_GATEWAY_HOST = "127.0.0.1"
$env:CLAUDE_GATEWAY_PORT = $port
if ($env:CLAUDE_SMOKE_USER_AGENT) { $env:CLAUDE_AI_USER_AGENT = $env:CLAUDE_SMOKE_USER_AGENT }

Write-Host "==> booting ephemeral gateway on :$port (memory DB)"
$srv = Start-Process -FilePath $PY -ArgumentList "-m","gateway" -PassThru -NoNewWindow `
  -RedirectStandardOutput "$env:TEMP\gw_smoke.log" -RedirectStandardError "$env:TEMP\gw_smoke.err"

function Wait-Health($url, $tries = 40) {
  for ($i = 0; $i -lt $tries; $i++) {
    try { if ((Invoke-WebRequest -Uri $url -UseBasicParsing -TimeoutSec 2).StatusCode -eq 200) { return $true } } catch {}
    Start-Sleep -Milliseconds 500
  }
  return $false
}

try {
  if (-not (Wait-Health "$base/health")) { Get-Content "$env:TEMP\gw_smoke.err"; throw "boot failed" }
  Write-Host "OK  gateway up (pid $($srv.Id))"

  $provBody = @{ cookies = $cookies; name = "smoke" }
  if ($env:CLAUDE_SMOKE_ORG_UUID) { $provBody.org_uuid = $env:CLAUDE_SMOKE_ORG_UUID }
  $prov = Invoke-RestMethod -Method Post -Uri "$base/system/keys/generate" `
    -Headers @{ "X-Admin-Token" = $adminToken } -ContentType "application/json" `
    -Body ($provBody | ConvertTo-Json -Depth 5 -Compress)
  $apiKey = $prov.key
  if (-not $apiKey) { throw "no key minted" }
  Write-Host "OK  minted API key (redacted)"

  function Check($name, $method, $path, $auth, $body, $want) {
    $headers = @{}
    if ($auth -eq "key") { $headers["Authorization"] = "Bearer $apiKey" }
    try {
      if ($body) {
        $r = Invoke-WebRequest -Method $method -Uri "$base$path" -Headers $headers -ContentType "application/json" -Body $body -UseBasicParsing
      } else {
        $r = Invoke-WebRequest -Method $method -Uri "$base$path" -Headers $headers -UseBasicParsing
      }
      $code = $r.StatusCode; $content = $r.Content
    } catch {
      $code = if ($_.Exception.Response) { [int]$_.Exception.Response.StatusCode } else { 0 }
      $content = "$($_.Exception.Message)"
    }
    $pass = ($code -eq 200) -and ((-not $want) -or ($content -match [regex]::Escape($want)))
    if ($pass) {
      Write-Host ("OK  {0,-24} PASS  http={1} kind=wiring" -f $name, $code)
    } else {
      $kind = if ($code -eq 429 -or $code -ge 500 -or $content -match "(?i)cloudflare|just a moment|cf-mitigated|challenge|rate.?limit|forbidden by anthropic") { "upstream" } else { "wiring" }
      Write-Warning ("{0,-24} FAIL  http={1} kind={2}" -f $name, $code, $kind)
      if ($kind -eq "wiring") { $script:wiringFails++ }
    }
  }

  Write-Host "==> running surface checks"
  Check "health"            "GET"  "/health"               "none" $null $null
  Check "v1/models"         "GET"  "/v1/models"            "key"  $null $null
  Check "v1/chats/list"     "GET"  "/v1/chats/list?limit=3" "key" $null $null
  Check "v1/prompt"         "POST" "/v1/prompt"            "key"  '{"text":"ping"}' $null
  Check "v1/chat-nonstream" "POST" "/v1/chat/completions"  "key"  '{"model":"claude-sonnet-4-6","messages":[{"role":"user","content":"say hi"}]}' $null
  Check "v1/chat-stream"    "POST" "/v1/chat/completions"  "key"  '{"model":"claude-sonnet-4-6","stream":true,"messages":[{"role":"user","content":"say hi"}]}' "[DONE]"

  Write-Host ""
  if ($wiringFails -eq 0) { Write-Host "OK  SMOKE PASSED - all gateway-wiring checks green"; exit 0 }
  Write-Error "SMOKE FAILED - $wiringFails gateway-wiring check(s) failed"; exit 1
}
finally {
  if ($srv -and -not $srv.HasExited) { Stop-Process -Id $srv.Id -Force -ErrorAction SilentlyContinue }
}
