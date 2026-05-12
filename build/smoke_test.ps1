#!/usr/bin/env pwsh
<#
.SYNOPSIS
  Prady OS v1.0.0 Smoke Test — Interactive service health check
.DESCRIPTION
  Validates that the Prady OS Docker Compose stack starts correctly
  and that all microservices respond to /health endpoints.
.EXAMPLE
  .\smoke_test.ps1
#>

param(
  [string]$ComposeFile = "docker-compose.dev.yml",
  [int]$HealthCheckTimeout = 30
)

$ErrorActionPreference = "Stop"

Write-Host "╔════════════════════════════════════════════════════╗" -ForegroundColor Cyan
Write-Host "║    Prady OS v1.0.0 Smoke Test                      ║" -ForegroundColor Cyan
Write-Host "╚════════════════════════════════════════════════════╝" -ForegroundColor Cyan
Write-Host ""

# Step 1: Start Docker Compose
Write-Host "📦 Starting Docker Compose stack..." -ForegroundColor Green
docker compose -f $ComposeFile up -d

if ($LASTEXITCODE -ne 0) {
  Write-Host "❌ Failed to start Docker Compose" -ForegroundColor Red
  exit 1
}

Write-Host "✅ Docker Compose started" -ForegroundColor Green
Write-Host ""

# Step 2: Wait for services to be ready
Write-Host "⏳ Waiting for services to stabilize..." -ForegroundColor Yellow
Start-Sleep -Seconds 5

# Step 3: Health check on key services
$services = @(
  @{ name = "prax-agent"; port = 3001 },
  @{ name = "vyrex-proxy"; port = 8080 },
  @{ name = "lumyn-bridge"; port = 9000 },
  @{ name = "auth-service"; port = 5000 }
)

$healthyCount = 0

foreach ($service in $services) {
  Write-Host "  Testing $($service.name)..." -ForegroundColor Gray
  $maxRetries = $HealthCheckTimeout
  $retry = 0
  $healthy = $false
  
  while ($retry -lt $maxRetries -and -not $healthy) {
    try {
      $response = Invoke-WebRequest -Uri "http://localhost:$($service.port)/health" `
        -Method GET -TimeoutSec 2 -ErrorAction Stop
      if ($response.StatusCode -eq 200) {
        Write-Host "    ✅ $($service.name) healthy" -ForegroundColor Green
        $healthy = $true
        $healthyCount++
      }
    }
    catch {
      $retry++
      if ($retry -lt $maxRetries) {
        Start-Sleep -Seconds 1
      }
    }
  }
  
  if (-not $healthy) {
    Write-Host "    ⚠️  $($service.name) not responding" -ForegroundColor Yellow
  }
}

Write-Host ""
Write-Host "📊 Health Check Results: $healthyCount/$($services.Count) services healthy" -ForegroundColor Cyan

# Step 4: Prompt for cleanup
Write-Host ""
Write-Host "🧹 Cleaning up..." -ForegroundColor Yellow
$response = Read-Host "Stop Docker Compose stack? (y/n)"

if ($response -eq "y" -or $response -eq "Y") {
  docker compose -f $ComposeFile down
  Write-Host "✅ Stack stopped and removed" -ForegroundColor Green
}
else {
  Write-Host "⚠️  Stack still running. Stop with: docker compose down" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "✅ Smoke test complete" -ForegroundColor Green
