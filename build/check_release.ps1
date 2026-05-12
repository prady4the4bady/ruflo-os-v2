#!/usr/bin/env pwsh
<#
.SYNOPSIS
  Prady OS v1.0.0 Release Verification Script
.DESCRIPTION
  Verifies that the GitHub Actions release pipeline ran successfully.
  Provides instructions for manual validation if needed.
.EXAMPLE
  .\check_release.ps1
#>

param(
  [string]$Owner = "prady4the4bady",
  [string]$Repo = "prady-os",
  [string]$Tag = "v1.0.0"
)

Write-Host "╔════════════════════════════════════════════════════╗" -ForegroundColor Cyan
Write-Host "║    Prady OS v1.0.0 Release Verification            ║" -ForegroundColor Cyan
Write-Host "╚════════════════════════════════════════════════════╝" -ForegroundColor Cyan
Write-Host ""

# Check if GitHub CLI is installed
$ghInstalled = Get-Command gh -ErrorAction SilentlyContinue
if (-not $ghInstalled) {
  Write-Host "⚠️  GitHub CLI not found. Install from https://cli.github.com/" -ForegroundColor Yellow
  Write-Host ""
  Write-Host "Manual verification steps:" -ForegroundColor Green
  Write-Host "  1. Visit: https://github.com/$Owner/$Repo/releases/tag/$Tag" -ForegroundColor Gray
  Write-Host "  2. Verify ISO artifact (prady-os.iso) is present" -ForegroundColor Gray
  Write-Host "  3. Verify SHA256 checksum file (prady-os.sha256) is present" -ForegroundColor Gray
  Write-Host "  4. Verify release description matches expectations" -ForegroundColor Gray
  Write-Host ""
  exit 0
}

# Use GitHub CLI to check release
Write-Host "📦 Checking GitHub release..." -ForegroundColor Green
Write-Host ""

try {
  $release = gh release view $Tag -R "$Owner/$Repo" --json "tagName,name,description,isLatest,isPrerelease" | ConvertFrom-Json
  
  Write-Host "Release: $($release.tagName)" -ForegroundColor Cyan
  Write-Host "Name: $($release.name)" -ForegroundColor Cyan
  Write-Host "Latest: $($release.isLatest)" -ForegroundColor Cyan
  Write-Host "Pre-release: $($release.isPrerelease)" -ForegroundColor Cyan
  
  Write-Host ""
  Write-Host "📄 Description (first 200 chars):" -ForegroundColor Green
  Write-Host "$($release.description.Substring(0, [Math]::Min(200, $release.description.Length)))..." -ForegroundColor Gray
  
  # Check for release assets
  Write-Host ""
  Write-Host "📦 Checking release assets..." -ForegroundColor Green
  
  $assets = gh release view $Tag -R "$Owner/$Repo" --json "assets" | ConvertFrom-Json
  
  $requiredAssets = @("prady-os.iso", "prady-os.sha256")
  foreach ($asset in $requiredAssets) {
    $found = $assets.assets | Where-Object { $_.name -eq $asset }
    if ($found) {
      Write-Host "  ✅ $asset present" -ForegroundColor Green
    }
    else {
      Write-Host "  ❌ $asset missing" -ForegroundColor Red
    }
  }
  
}
catch {
  Write-Host "❌ Error checking release: $_" -ForegroundColor Red
  exit 1
}

Write-Host ""
Write-Host "✅ Release verification complete" -ForegroundColor Green
