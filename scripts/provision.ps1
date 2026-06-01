# Onboard a claude.ai account and mint an API key (Windows / PowerShell).
#
# Cookies come from env (never an argument). For Cloudflare you need the FULL jar
# (sessionKey + cf_clearance + __cf_bm + _cfuvid) from a browser that passes the
# challenge on this IP:
#
#   $env:CLAUDE_COOKIES='sessionKey=...; cf_clearance=...; __cf_bm=...; _cfuvid=...'
#   scripts\provision.ps1 -Org <uuid> -Name cli
#   # bare sessionKey also works (org-scoped calls 403 without cf_clearance):
#   $env:CLAUDE_SESSION_KEY="sk-ant-sid02-..."; scripts\provision.ps1
#
# Requires CLAUDE_GATEWAY_ADMIN_TOKEN and a running gateway started with
# CLAUDE_AI_USER_AGENT matching the browser the cookies came from.
param(
  [string]$Org = "",
  [string]$Name = "provisioned"
)
$ErrorActionPreference = "Stop"

$admin = $env:CLAUDE_GATEWAY_ADMIN_TOKEN
if (-not $admin) { Write-Error "CLAUDE_GATEWAY_ADMIN_TOKEN must be set (see .env)"; exit 1 }

$raw = $env:CLAUDE_COOKIES
if (-not $raw -and $env:CLAUDE_SESSION_KEY) { $raw = "sessionKey=$($env:CLAUDE_SESSION_KEY)" }
if (-not $raw) { Write-Error "set CLAUDE_COOKIES (full jar) or CLAUDE_SESSION_KEY"; exit 1 }

$cookies = @{}
if ($raw -match "=") {
  foreach ($pair in $raw.Split(";")) {
    $p = $pair.Trim()
    $i = $p.IndexOf("=")
    if ($i -gt 0) { $cookies[$p.Substring(0, $i).Trim()] = $p.Substring($i + 1).Trim() }
  }
} else {
  $cookies["sessionKey"] = $raw.Trim()
}

$gwHost = if ($env:CLAUDE_GATEWAY_HOST -and $env:CLAUDE_GATEWAY_HOST -ne "0.0.0.0") { $env:CLAUDE_GATEWAY_HOST } else { "127.0.0.1" }
$port = if ($env:CLAUDE_GATEWAY_PORT) { $env:CLAUDE_GATEWAY_PORT } else { "8081" }
$url  = "http://${gwHost}:${port}/system/keys/generate"

$bodyObj = @{ cookies = $cookies; name = $Name }
if ($Org) { $bodyObj.org_uuid = $Org }
$body = $bodyObj | ConvertTo-Json -Depth 5 -Compress

Write-Host "==> provisioning account + key at $url (cookies redacted)"
$resp = Invoke-RestMethod -Method Post -Uri $url -Headers @{ "X-Admin-Token" = $admin } `
  -ContentType "application/json" -Body $body
if (-not $resp.key) { Write-Error "no key in response: $($resp | ConvertTo-Json -Compress)"; exit 1 }
Write-Host "OK  API key (shown once): $($resp.key)"
