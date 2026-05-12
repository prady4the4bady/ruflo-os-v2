#!/usr/bin/env pwsh
# Prady OS v1.0.0 Smoke Test
# Usage: pwsh build/smoke_test.ps1

$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

Write-Host ""
Write-Host "╔════════════════════════════════════════╗"
Write-Host "║   Prady OS v1.0.0 Smoke Test           ║"
Write-Host "╚════════════════════════════════════════╝"
Write-Host ""

# Check if stack is already running
$running = docker compose -f docker-compose.dev.yml `
  ps --format json 2>$null
if (-not $running) {
  Write-Host "📦 Starting Docker Compose stack..."
  docker compose -f docker-compose.dev.yml up -d --wait
  if ($LASTEXITCODE -ne 0) {
    Write-Host "ERROR: docker compose up failed"
    exit 1
  }
  Write-Host "✅ Stack started"
  Write-Host "⏳ Waiting 25 seconds for services to stabilise..."
  Start-Sleep -Seconds 25
} else {
  Write-Host "✅ Stack already running — skipping startup"
}

# Build the service → port map directly from compose config
# This reads the actual published ports from the compose file
Write-Host ""
Write-Host "🔍 Reading service port map from compose config..."

$composeConfig = docker compose -f docker-compose.dev.yml `
  config --format json 2>$null | ConvertFrom-Json
$servicePortMap = @{}

foreach ($svcName in $composeConfig.services.PSObject.Properties.Name) {
  $svc = $composeConfig.services.$svcName
  if ($svc.ports) {
    foreach ($portEntry in $svc.ports) {
      # portEntry.published is the host port
      $hostPort = $portEntry.published
      if ($hostPort -and $hostPort -gt 0) {
        $servicePortMap[$svcName] = $hostPort
        break  # take the first port mapping
      }
    }
  }
}

Write-Host "Found $($servicePortMap.Count) services with ports"
Write-Host ""
Write-Host "🏥 Running health checks..."
Write-Host ""

$ok = 0
$fail = @()
$skip = @()

foreach ($svcName in ($servicePortMap.Keys | Sort-Object)) {
  $port = $servicePortMap[$svcName]
  if (-not $port) {
    $skip += $svcName
    continue
  }

  # postgres speaks the wire protocol, not HTTP — use pg_isready
  if ($svcName -eq "postgres") {
    $pgCheck = docker compose -f docker-compose.dev.yml `
      exec -T postgres pg_isready -U kryos 2>&1
    if ($LASTEXITCODE -eq 0) {
      Write-Host "  ✅ postgres (port $port — pg_isready OK)"
      $ok++
    } else {
      Write-Host "  ❌ postgres — $pgCheck"
      $fail += "postgres:$port"
    }
    continue
  }

  # redis also does not speak HTTP — use redis-cli ping
  if ($svcName -eq "redis") {
    $redisCheck = docker compose -f docker-compose.dev.yml `
      exec -T redis redis-cli ping 2>&1
    if ($LASTEXITCODE -eq 0 -and $redisCheck -match "PONG") {
      Write-Host "  ✅ redis (port $port — PING PONG)"
      $ok++
    } else {
      Write-Host "  ❌ redis — $redisCheck"
      $fail += "redis:$port"
    }
    continue
  }

  # Try /health first, then /healthz, then root
  $endpoints = @("/health", "/healthz", "/")
  $responded = $false

  foreach ($endpoint in $endpoints) {
    try {
      $r = Invoke-RestMethod `
        "http://localhost:$port$endpoint" `
        -TimeoutSec 5 -ErrorAction Stop
      if ($r.status -eq "ok" -or
          $r.status -eq "healthy" -or
          $endpoint -eq "/") {
        Write-Host "  ✅ $svcName (port $port$endpoint)"
        $ok++
        $responded = $true
        break
      }
    } catch {
      # try next endpoint
    }
  }

  if (-not $responded) {
    # Try raw HTTP status check (some services return non-JSON)
    try {
      $resp = Invoke-WebRequest `
        "http://localhost:$port/health" `
        -TimeoutSec 5 -ErrorAction Stop
      if ($resp.StatusCode -eq 200) {
        Write-Host "  ✅ $svcName (port $port — HTTP 200)"
        $ok++
        $responded = $true
      }
    } catch {
      Write-Host "  ❌ $svcName (port $port) — unreachable"
      $fail += "${svcName}:${port}"
    }
  }
}

$total = $servicePortMap.Count
Write-Host ""
Write-Host "════════════════════════════════════════"
Write-Host "  Results: $ok / $total services healthy"
if ($skip.Count -gt 0) {
  Write-Host "  Skipped (no port): $($skip -join ', ')"
}
Write-Host "════════════════════════════════════════"

if ($fail.Count -eq 0) {
  Write-Host ""
  Write-Host "  ✅ ALL SERVICES HEALTHY"
  Write-Host "  🚀 PRADY OS v1.0.0 IS FULLY VERIFIED"
  Write-Host "     github.com/prady4the4bady/prady-os"
  Write-Host ""
} else {
  Write-Host ""
  Write-Host "  ⚠️  FAILED SERVICES:"
  foreach ($f in $fail) {
    $name = $f.Split(":")[0]
    $port = $f.Split(":")[1]
    Write-Host "    ❌ ${name} (port ${port})"
    Write-Host "       docker compose -f docker-compose.dev.yml logs ${name}"
  }
  Write-Host ""
  Write-Host "  Common fixes:"
  Write-Host "    ModuleNotFoundError → add dep to requirements.txt"
  Write-Host "    PermissionError     → check USER in Dockerfile"
  Write-Host "    Address in use      → netstat -ano | findstr ${port}"
  Write-Host "    DB init error       → check volume mounts in compose"
  Write-Host ""
}

# Ask to stop
if ($env:SMOKE_TEST_NONINTERACTIVE -eq "1") {
  Write-Host "Stack still running. (non-interactive mode)"
  Write-Host "Stop with: docker compose -f docker-compose.dev.yml down"
  if ($fail.Count -gt 0) { exit 1 } else { exit 0 }
}

$stop = Read-Host "Stop Docker Compose stack? (y/n)"
if ($stop -eq "y") {
  docker compose -f docker-compose.dev.yml down
  Write-Host "✅ Stack stopped"
} else {
  Write-Host "Stack still running."
  Write-Host "Stop with: docker compose -f docker-compose.dev.yml down"
}
