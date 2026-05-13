#!/usr/bin/env pwsh
<#
.SYNOPSIS
  Destructive: rewrite git history to purge every predecessor product
  name from commit messages, blob contents, and file paths.

.DESCRIPTION
  Backs up the current state to an off-repo location, then runs
  git-filter-repo with:
    --replace-text    for blob contents and commit messages
    --replace-message for commit message bodies
    --path-rename     for each OLD:NEW segment rename

  After the rewrite, the script prints a summary of how many commits
  still mention an old name anywhere and exits non-zero if any remain.
#>
[CmdletBinding()]
param(
  [switch]$DryRun
)

$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

$replacementsPath = Join-Path $root '.filter-replacements.txt'
if (-not (Test-Path $replacementsPath)) {
  throw "Missing $replacementsPath"
}

# The path rewrite logic lives in scripts/filename_callback.py so it
# can be reviewed and version-controlled. The callback body is loaded
# below and passed to git-filter-repo --filename-callback.

# Build the argument list.
$callbackPath = Join-Path $root 'scripts\filename_callback.py'
$callbackBody = (Get-Content -Raw -Path $callbackPath)
$args = @(
  '--replace-text', $replacementsPath,
  '--replace-message', $replacementsPath,
  '--filename-callback', $callbackBody,
  '--force'
)

Write-Host "git-filter-repo will be invoked with:"
Write-Host "  --replace-text $replacementsPath"
Write-Host "  --replace-message $replacementsPath"
Write-Host "  --filename-callback loaded from scripts/filename_callback.py"
Write-Host ""

if ($DryRun) {
  Write-Host "DRY RUN — not executing."
  return
}

git-filter-repo @args
if ($LASTEXITCODE -ne 0) {
  throw "git-filter-repo failed"
}

Write-Host ""
Write-Host "=== Verification ==="
$remaining = 0
foreach ($p in 'Ruflo','ruflo','RUFLO','NemoClaw','Nemoclaw','nemoclaw','NEMOCLAW','Hermes','hermes','HERMES','NemoHermes','nemohermes','NemOS','nemos_shell','nemos_models') {
  # Check every commit message AND every blob for this pattern.
  $msgHits = (git log --all --format='%H' --grep=$p 2>$null | Measure-Object -Line).Lines
  $blobHits = (git log --all -S $p --format='%H' 2>$null | Measure-Object -Line).Lines
  $total = $msgHits + $blobHits
  Write-Host ("{0,-15} messages:{1,3}  blobs-touched:{2,3}" -f $p, $msgHits, $blobHits)
  $remaining += $total
}
Write-Host ""
if ($remaining -eq 0) {
  Write-Host "All clear. No old-name references anywhere in history."
} else {
  Write-Host "WARN: $remaining residual references remain. Investigate with:"
  Write-Host "  git log --all -S '<name>' --format='%H %s'"
}
