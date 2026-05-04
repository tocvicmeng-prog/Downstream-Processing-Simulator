# Render every Mermaid source in docs/figures/source/ to a sibling PNG
# in docs/figures/. Invokes @mermaid-js/mermaid-cli via npx (no global
# install required); first run downloads ~150 MB of dependencies.
#
# Usage (from repo root):
#   docs\figures\render.ps1

$ErrorActionPreference = "Stop"

$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$source = Join-Path $root "source"
$out = $root

# Wide layout for flowcharts; narrower for the tier-inheritance / FSM diagrams.
$widths = @{
    "01_lifecycle_dataflow"  = @{ W = 1600; H = 600 }
    "02_tier_inheritance"    = @{ W = 1400; H = 360 }
    "03_acs_sequence_fsm"    = @{ W = 1600; H = 460 }
    "04_cfd_pbe_pipeline"    = @{ W = 1600; H = 600 }
}

Get-ChildItem -Path $source -Filter "*.mmd" | ForEach-Object {
    $stem = $_.BaseName
    $w = if ($widths.ContainsKey($stem)) { $widths[$stem].W } else { 1600 }
    $h = if ($widths.ContainsKey($stem)) { $widths[$stem].H } else { 600 }
    $inFile = $_.FullName
    $outFile = Join-Path $out "$stem.png"
    Write-Host "[render] $stem  (${w}x${h})"
    & npx --yes -p "@mermaid-js/mermaid-cli@10" mmdc `
        -i $inFile -o $outFile -b white -w $w -H $h -t default
    if ($LASTEXITCODE -ne 0) { throw "mmdc failed for $stem" }
}

Write-Host "[render] DONE. PNGs in $out"
