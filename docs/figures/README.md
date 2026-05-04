# DPSim figure assets

PNG renders of every Mermaid diagram embedded in the project's top-level
`README.md`. GitHub renders the `mermaid` code blocks natively; these PNGs
are for offline / print contexts (the bundled First Edition PDF, slide decks,
grant materials) where Mermaid is not available.

## Figures in this set

| # | File | Where it appears | Caption / scientific message |
|---|---|---|---|
| 01 | `01_lifecycle_dataflow.png` | README hero | M1 → M2 → M3 dataflow with ProcessRecipe input, ProcessDossier output, and the calibration store as the dotted feedback edge that promotes evidence tiers. |
| 02 | `02_tier_inheritance.png` | README §Confidence Model | Evidence-tier inheritance rule: a downstream module's tier is capped by its upstream input's tier. Enforced in `RunReport.compute_min_tier`. |
| 03 | `03_acs_sequence_fsm.png` | README §Capabilities · Modelling | The canonical M2 chemistry order *ACS Converter → Linker Arm → Ligand → Ion-charging*, enforced by the v0.5.0 G6 sequence FSM at recipe-load time. |
| 04 | `04_cfd_pbe_pipeline.png` | README §Hardware Geometry and CFD-PBE Coupling | The OpenFOAM → schema-v1.0 zones.json → zonal-PBE pipeline that resolves slot-exit breakage (the Padron 2005 / Hall 2011 region carrying 80–95 % of M1 breakage events). |

## Source files

Mermaid sources live in [`source/`](source/). Edit the `.mmd` file, then
re-render with the script below; the README continues to use the inline
Mermaid block (sources here are mirrors for offline / print use).

## Regenerating the PNGs

The renderer is the `@mermaid-js/mermaid-cli` package, invoked via `npx`.
First run downloads ~150 MB of dependencies (puppeteer + chromium); later
runs are fast.

### From the repo root

```powershell
# Windows PowerShell
docs\figures\render.ps1
```

```bash
# Bash / WSL / macOS
docs/figures/render.sh
```

### Manual one-off

```bash
npx -p @mermaid-js/mermaid-cli@10 mmdc \
    -i docs/figures/source/01_lifecycle_dataflow.mmd \
    -o docs/figures/01_lifecycle_dataflow.png \
    -b white -w 1600 -H 600 -t default
```

## Style conventions

- **Background:** white (`-b white`) — prints cleanly and works inside the
  PDF manual on a light page.
- **Theme:** `default` — neutral palette so the PNGs do not clash with the
  manual's Source Sans typography.
- **Aspect ratio:** wide flowcharts (figures 01, 04) are rendered at
  1600 × 600 px; the simpler tier-inheritance and FSM diagrams (02, 03)
  default to 1400 × 400 px.
- **Filenames:** zero-padded ordinal prefixes so `ls` orders them in the
  same sequence the README presents them.

## When to regenerate

- After any edit to `README.md` that changes the inline Mermaid blocks,
  re-export the matching `.mmd` source here and re-render.
- After a Mermaid-CLI major version bump, sanity-check that the PNGs still
  match the GitHub-rendered version.
- Before a release that bundles the PDF manual (the manual's build step
  picks up the latest PNGs in this folder).
