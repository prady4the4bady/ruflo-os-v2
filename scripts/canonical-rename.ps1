#!/usr/bin/env pwsh
<#
.SYNOPSIS
  Perform the canonical rename sweep for Prady OS v1.0.0.

.DESCRIPTION
  Rewrites old product names to their canonical equivalents across every
  tracked file in the repository. Preserves case (Prady -> Prady,
  prady -> prady, PRADY -> PRADY, etc.) and uses longest-match-first
  ordering so that multi-word names are rewritten before their
  single-word prefixes.

  The script never touches binary files, the .git directory, node_modules,
  venvs, mypy/pytest caches, or vendored tool caches.

.PARAMETER DryRun
  When set, prints the files that would be changed but writes nothing.

.EXAMPLE
  pwsh scripts/canonical-rename.ps1 -DryRun
  pwsh scripts/canonical-rename.ps1
#>
[CmdletBinding()]
param(
  [switch]$DryRun
)

$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

# Ordered: multi-word entries first so they match before single-word prefixes.
# Each entry: [Pattern, Replacement]. Pattern is treated as literal text
# (case-sensitive, no regex) to avoid accidental breakage of URLs etc.
$literalMap = @(
  @('Prady OS',        'Prady OS'),
  @('prady-os',        'prady-os'),
  @('PRADY_OS',        'PRADY_OS'),
  @('PRADY-OS',        'PRADY-OS'),
  @('Prax Agent',     'Prax Agent'),
  @('prax-agent',     'prax-agent'),
  @('Prax-Agent',     'Prax-Agent'),
  @('PRAX_AGENT',     'PRAX_AGENT'),
  @('Vyrex',        'Vyrex'),
  @('vyrex',        'vyrex'),
  @('VYREX',        'VYREX'),
  @('VyrexLumyn',      'VyrexLumyn'),
  @('vyrex-lumyn',      'vyrex-lumyn'),
  @('Lumyn',    'Lumyn'),
  @('lumyn',    'lumyn'),
  @('Lumyn',     'Lumyn'),
  @('Lumyn',          'Lumyn'),
  @('lumyn',          'lumyn'),
  @('LUMYN',          'LUMYN'),
  @('Prady',           'Prady'),
  @('prady',           'prady'),
  @('PRADY',           'PRADY')
)

# Paths we never touch.
$skipDirPatterns = @(
  '\.git[\\/]',
  'node_modules[\\/]',
  '__pycache__[\\/]',
  '\.venv[\\/]',
  '\.mypy_cache[\\/]',
  '\.pytest_cache[\\/]',
  '\.idea[\\/]'
)

# Binary / generated file extensions we never touch.
$skipExtensions = @(
  '.png','.jpg','.jpeg','.gif','.bmp','.ico','.svg',
  '.pdf','.zip','.tar','.gz','.xz','.7z','.whl',
  '.woff','.woff2','.ttf','.eot',
  '.pyc','.pyo','.class','.o','.so','.dll','.exe',
  '.sqlite','.db','.db-shm','.db-wal',
  '.tsbuildinfo'
)

function Should-Skip {
  param([string]$Path)
  foreach ($pat in $skipDirPatterns) {
    if ($Path -match $pat) { return $true }
  }
  $ext = [IO.Path]::GetExtension($Path).ToLower()
  if ($skipExtensions -contains $ext) { return $true }
  return $false
}

function Rewrite-File {
  param([string]$Path)
  $bytes = [IO.File]::ReadAllBytes($Path)
  if ($bytes.Length -eq 0) { return $false }
  # Heuristic binary detection: null byte in first 8k
  $sample = $bytes[0..([Math]::Min($bytes.Length - 1, 8192))]
  if ($sample -contains 0) { return $false }

  $text = [Text.Encoding]::UTF8.GetString($bytes)
  $original = $text
  foreach ($pair in $literalMap) {
    $text = $text.Replace($pair[0], $pair[1])
  }
  if ($text -ne $original) {
    if (-not $DryRun) {
      # Write without BOM, preserve line endings as-is.
      [IO.File]::WriteAllText($Path, $text, (New-Object Text.UTF8Encoding($false)))
    }
    return $true
  }
  return $false
}

$tracked = git ls-files | Where-Object { -not (Should-Skip $_) }
$changed = @()
foreach ($rel in $tracked) {
  $full = Join-Path $root $rel
  if (-not (Test-Path $full -PathType Leaf)) { continue }
  try {
    if (Rewrite-File $full) { $changed += $rel }
  } catch {
    Write-Warning "Could not rewrite ${rel}: $($_.Exception.Message)"
  }
}

Write-Host ""
Write-Host "Rewrote text in $($changed.Count) files."
if ($DryRun) {
  $changed | Select-Object -First 40 | ForEach-Object { Write-Host "  $_" }
  if ($changed.Count -gt 40) { Write-Host "  ... and $($changed.Count - 40) more" }
}
