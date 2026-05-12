#!/usr/bin/env pwsh
<#
.SYNOPSIS
  Rename files and directories that still contain old product names.

.DESCRIPTION
  Applies git-aware renames (git mv) for every tracked path that
  contains 'prady', 'vyrex', or 'lumyn' (case-insensitive).
  Processes deepest paths first so directory renames don't break
  pending child renames.
#>
[CmdletBinding()]
param(
  [switch]$DryRun
)

$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

# Case-preserving segment map: apply per path-segment, ordered so that
# multi-word / specific names match before single-word ones.
$segmentMap = @(
  @('prax-runtime',    'prax-runtime'),
  @('prax-agent',            'prax-agent'),
  @('prady-firstboot-check',  'prady-firstboot-check'),
  @('prady-firstboot',        'prady-firstboot'),
  @('prady-session',          'prady-session'),
  @('prady-lumyn',           'prady-lumyn'),
  @('prady-lumyn',     'prady-lumyn'),
  @('prady-vyrex-proxy',   'prady-vyrex-proxy'),
  @('prady-aqua-shell',       'prady-desktop-shell'),
  @('prady-model-gateway',    'prady-model-gateway'),
  @('prady-screen-agent',     'prady-screen-agent'),
  @('prady-workflow-engine',  'prady-workflow-engine'),
  @('prady-audit-log',        'prady-audit-log'),
  @('prady-automation',       'prady-automation'),
  @('prady-computer-use',     'prady-computer-use'),
  @('prady-memory-service',   'prady-memory-service'),
  @('prady-model-hub',        'prady-model-hub'),
  @('prady-notification-bus', 'prady-notification-bus'),
  @('prady-package-manager',  'prady-package-manager'),
  @('prady-persona-service',  'prady-persona-service'),
  @('prady-security-policy',  'prady-security-policy'),
  @('prady-swarm-coordinator','prady-swarm-coordinator'),
  @('prady-task-scheduler',   'prady-task-scheduler'),
  @('prady-watchdog',         'prady-watchdog'),
  @('prady-wayland-mcp',      'prady-wayland-mcp'),
  @('prady-ai',               'prady-ai'),
  @('prady-base',             'prady-base'),
  @('prady-desktop',          'prady-desktop'),
  @('prady-setup',            'prady-setup'),
  @('prady-logo',             'prady-logo'),
  @('Prady',                  'Prady'),
  @('prady',                  'prady'),
  @('PRADY',                  'PRADY'),
  @('Vyrex',               'Vyrex'),
  @('Vyrex',               'Vyrex'),
  @('vyrex',               'vyrex'),
  @('VYREX',               'VYREX'),
  @('LumynTaskPanel',        'LumynTaskPanel'),
  @('LumynConsole',          'LumynConsole'),
  @('lumyn',           'lumyn'),
  @('lumyn-config',          'lumyn-config'),
  @('lumyn-skills',          'lumyn-skills'),
  @('lumyn_bridge',          'lumyn_bridge'),
  @('lumyn_format',          'lumyn_format'),
  @('lumyn_policy',          'lumyn_policy'),
  @('lumyn',                 'lumyn'),
  @('Lumyn',                 'Lumyn'),
  @('LUMYN',                 'LUMYN')
)

function Get-NewPath {
  param([string]$OldRel)
  $segments = $OldRel -split '/'
  for ($i = 0; $i -lt $segments.Length; $i++) {
    foreach ($pair in $segmentMap) {
      # Replace only inside this single segment.
      $segments[$i] = $segments[$i].Replace($pair[0], $pair[1])
    }
  }
  return ($segments -join '/')
}

$tracked = git ls-files | Where-Object {
  $_ -match '(?i)(prady|vyrex|lumyn)'
} | Sort-Object -Property @{Expression={ ($_ -split '/').Count }; Descending=$true}, { $_ }

$renames = @()
foreach ($old in $tracked) {
  $new = Get-NewPath $old
  if ($new -eq $old) { continue }
  $renames += ,@($old, $new)
}

Write-Host "Planned renames: $($renames.Count)"
foreach ($r in $renames) {
  Write-Host "  $($r[0])  ->  $($r[1])"
  if (-not $DryRun) {
    # git mv handles creating the destination directory automatically.
    # It also moves on the filesystem AND stages the rename.
    git mv -- $r[0] $r[1] 2>&1 | Out-Null
    if ($LASTEXITCODE -ne 0) {
      Write-Warning "git mv failed: $($r[0]) -> $($r[1])"
    }
  }
}

Write-Host ""
Write-Host ($(if ($DryRun) { "DRY RUN — no changes." } else { "Done." }))
