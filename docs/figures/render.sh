#!/usr/bin/env bash
# Render every Mermaid source in docs/figures/source/ to a sibling PNG
# in docs/figures/. Invokes @mermaid-js/mermaid-cli via npx (no global
# install required); first run downloads ~150 MB of dependencies.
#
# Usage (from repo root):
#   docs/figures/render.sh

set -euo pipefail

root="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
src="$root/source"
out="$root"

declare -A W H
W["01_lifecycle_dataflow"]=1600;  H["01_lifecycle_dataflow"]=600
W["02_tier_inheritance"]=1400;    H["02_tier_inheritance"]=360
W["03_acs_sequence_fsm"]=1600;    H["03_acs_sequence_fsm"]=460
W["04_cfd_pbe_pipeline"]=1600;    H["04_cfd_pbe_pipeline"]=600

for f in "$src"/*.mmd; do
    stem="$(basename "$f" .mmd)"
    w="${W[$stem]:-1600}"
    h="${H[$stem]:-600}"
    echo "[render] $stem  (${w}x${h})"
    npx --yes -p "@mermaid-js/mermaid-cli@10" mmdc \
        -i "$f" -o "$out/$stem.png" -b white -w "$w" -H "$h" -t default
done

echo "[render] DONE. PNGs in $out"
