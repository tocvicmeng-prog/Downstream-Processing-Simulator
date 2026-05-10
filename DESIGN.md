# Design System — DPSim

> **v10.0 — Research Journal.** Replaces the v9.0 Industrial-Utilitarian system on
> 2026-05-11. Read this before making any visual or UI decisions. Flag any code
> that deviates in QA mode.
>
> Preview artifact (HTML, dark + light register): `~/.gstack/projects/tocvicmeng-prog-Downstream-Processing-Simulator/designs/research-journal-20260511-0248/preview.html`

## Product Context

- **What this is:** Multi-scale simulator for the polysaccharide microsphere → functionalized affinity media → packed-bed chromatography lifecycle (M1 fabrication → M2 functionalization → M3 affinity chromatography). Forked from the upstream EmulSim microsphere-fabrication codebase and re-scoped around downstream processing; produced by Holocyte Pty Ltd / GMExpression.
- **Who it's for:** Three audiences served by one publication at different depths.
  - *Lab tool (depth 1):* Downstream-processing scientists and technicians running production simulations. Power users; data-density takes priority.
  - *Teaching mode (depth 2):* Junior researchers learning packed-bed chromatography from first principles. Editorial pacing with marginalia for scientific commentary.
  - *Public docs portal (depth 3):* Readers of the methods, ADRs, and limitations docs. Long-form scientific reading register. Replaces / extends the PDF user manual.
  - *Adjacent stakeholders served by the same surfaces:* IP auditors, chief economists reviewing COGS, materials-science researchers.
- **Space:** Scientific publication ecosystem. Peer set is **Distill, Nature interactive features, MIT Press scientific monographs, Bell Labs technical reports**. **NOT** modern data-SaaS dashboards.
- **Project type:** Streamlit-based desktop/web scientific instrument that doubles as a live research journal.

## Aesthetic Direction

- **Direction:** **Research Journal** — Editorial publication foundation with utilitarian discipline for data surfaces. The product reads like a peer-reviewable scientific publication that happens to compute live.
- **Decoration level:** Minimal-with-typographic-craft. Decoration is *typographic*: drop caps for docs, marginalia / side notes (Tufte / Distill pattern) for teaching commentary, hairline rules between sections. **No** gradients, **no** decorative blobs, **no** icon circles, **no** drop shadows.
- **Mood:** Restrained. Citation-quality. Carries the same posture as the product itself — physics-anchored, evidence-graded, honest about uncertainty.
- **North stars:** Distill.pub (editorial scientific publication), Stripe Press (book-quality web register), Quanta Magazine (serif-headline + sans-body discipline), Bell Labs technical reports (lineage signal).
- **Anti-north-stars:** Anything that looks like a Stripe / Linear / Vercel knockoff. Anything with a purple or violet gradient as the primary accent. Anything centered. Generic "modern data SaaS" register.

## Surfaces and registers

The same design system stretches across three surfaces. Same triad, same palette, same component vocabulary; density and register shift by surface.

| Surface | Default register | Density | Layout | Primary type |
|---|---|---|---|---|
| Tool (M1 / M2 / M3 active screens) | Dark | Compact 4/8 | Three-zone (sidebar nav · main · evidence inspector) | Plex Sans + Plex Mono |
| Teaching mode (junior researcher onboarding) | Light | Editorial 8/16/24 | Editorial column (~640px) + marginalia rail (~200px) + breakout figures (~960px) | Source Serif 4 + Plex Sans |
| Docs portal (methods, ADRs, manual) | Light | Editorial 8/16/24 | TOC sidebar + editorial article + marginalia rail | Source Serif 4 + Plex Sans + Plex Mono |

A user moving from the tool into the docs feels they are reading the same publication, not switching apps.

## Typography

A triad. **Source Serif 4 · IBM Plex Sans · IBM Plex Mono.** Loaded via Google Fonts CDN in `app.py` head injection (see `src/dpsim/visualization/app.py`).

| Role | Font | Weight | Size | Rationale |
|---|---|---|---|---|
| Display / Hero (H1) | **Source Serif 4** | 600 | 28-36px | Transitional serif. Carries publication register before a single word is read. The biggest swing in the system. |
| Section header (H2) | Source Serif 4 | 600 | 20-24px | |
| Editorial deck / standfirst | Source Serif 4 italic | 400 | 17-19px | Used in docs / teaching. Italic carries the "subtitle of a feature" register. |
| Body — editorial (docs / teaching) | Source Serif 4 | 400 | 17px / 1.65 | Generous reading rhythm. Long-form articles. |
| Body — UI (tool surface) | **IBM Plex Sans** | 400-500 | 14px / 1.45 | Compact and dense. IBM's scientific computing typographic heritage; says "lineage" not "trendy." |
| UI labels / sidebar / chips | IBM Plex Sans | 500 | 11-12px | Uppercase, letterspaced 0.08-0.12em for chip/eyebrow labels. |
| Data / metrics / tables | **IBM Plex Mono** | 400-500 | 14px (body), 26-28px (metric values) | Tabular numerals enabled (`font-feature-settings: "tnum"`). Scientific data must align on the decimal point. |
| Equations / SMILES / code | IBM Plex Mono | 400 | 13-14px | Deep Unicode coverage: µ α β γ χ σ Ω → ↔ ∂ ∇ ∫. Pairs perfectly with Plex Sans. |
| Drop cap (docs only, opening paragraph) | Source Serif 4 | 600 | 60px | Float-left, 60px size, 0.85 line-height, accent-gold color. |

**Loading strategy:** Google Fonts `<link>` tag in page config. No self-hosting needed; repo stays lean.

**Do not use:** Geist (Vercel-coded, trending), Inter, Roboto, Arial, Helvetica, Source Sans Pro (Streamlit default), Open Sans, Montserrat, Poppins, Comic Sans, Papyrus.

**Why Source Serif 4 over Newsreader / Charter / Adobe Caslon:** Open-source from Adobe (no license headache), excellent at all sizes from 11px to 60px, optical-size axis available, italic has real character. Newsreader is a strong runner-up; switch only if Source Serif 4 ships a regression.

**Why IBM Plex over Geist:** Plex carries scientific computing heritage (loved in academic typesetting, IBM's research lineage). Geist is the trending choice in 2025-26 SaaS. We deliberately reject the trending choice — heritage signal that competitors can't fake by adopting next year's hot font.

## Color

**Restrained-with-signature.** Replacing the v9.0 cool slate + teal palette with a **warm cream-paper / ink / gold** register. Echoes the printed scientific publication tradition. The plotly scientific charts (DSD, phase field, breakthrough curves) remain the primary chromatic output; brand colors must not compete with them.

### Dark register — tool surface (default for M1 / M2 / M3)

| Token | Hex | Usage |
|---|---|---|
| `ink-deep` | `#0E0E10` | Page background |
| `ink-surface` | `#1A1A1F` | Surface (cards, inputs, plot frames) |
| `ink-deepest` | `#07070A` | Sidebar / inspector rail |
| `bone` | `#E8E4DA` | Primary text |
| `bone-muted` | `#8C8780` | Secondary / muted text |
| `bone-faint` | `#5A554F` | Faint text (timestamps, captions) |
| `gold-400` | `#D4B26A` | Accent — links, active states, citation chips, focus rings |
| `gold-300` | `#E5C485` | Hover state on accent |
| `gold-soft` | `rgba(212, 178, 106, 0.12)` | Accent-soft fill (button focus halo, table-row hover) |
| `rule` | `rgba(232, 228, 218, 0.16)` | Hairline rule (section dividers) |
| `border` | `rgba(232, 228, 218, 0.10)` | Component border |

### Light register — docs / teaching surface (default for docs portal)

| Token | Hex | Usage |
|---|---|---|
| `paper` | `#FAF7F0` | Page background — warm cream |
| `paper-surface` | `#F2EDDD` | Surface (cards, sidebar fill) |
| `paper-deepest` | `#EDE5CF` | Deep paper (toc fill on hover) |
| `ink` | `#1A1A1A` | Primary text |
| `ink-muted` | `#5C5750` | Secondary / muted text |
| `ink-faint` | `#8C8780` | Faint text (eyebrow, captions) |
| `gold-600` | `#B0904A` | Accent — links, citation chips, drop cap |
| `gold-700` | `#946F2C` | Hover state on accent |
| `gold-soft` | `rgba(176, 144, 74, 0.14)` | Accent-soft fill |
| `rule` | `rgba(26, 26, 26, 0.18)` | Hairline rule |
| `border` | `rgba(26, 26, 26, 0.10)` | Component border |
| `paper-tint` | `rgba(120, 95, 50, 0.025)` | Subtle paper-grain texture overlay (docs only — never on tool) |

### Evidence tier semantic colors (desaturated — printed feel)

These must map to the `ModelEvidenceTier` enum in `datatypes.py`. Hues shifted toward forest / olive / burnt-amber / rust / oxblood — printed scientific publication, not a digital chip.

| Tier / state | Light hex | Dark hex | Usage |
|---|---|---|---|
| `VALIDATED_QUANTITATIVE` | `#2D7A3E` | `#4FA86A` | Evidence badge "VALIDATED" |
| `CALIBRATED_LOCAL` | `#4A8B3A` | `#6EAE56` | Evidence badge "CALIBRATED" |
| `SEMI_QUANTITATIVE` | `#B07820` | `#D9A24A` | Evidence badge "SEMI-QUANTITATIVE" |
| `QUALITATIVE_TREND` | `#A24A1F` | `#C97A4A` | Evidence badge "QUALITATIVE TREND" |
| `UNSUPPORTED` | `#8E2929` | `#C25555` | Evidence badge "UNSUPPORTED" |
| `info` | `#3B6BA0` | `#7AA0CC` | Neutral informational banners (rare — prefer typographic emphasis) |
| `success` | `#2D7A3E` | `#4FA86A` | Success callouts |
| `warning` | `#B07820` | `#D9A24A` | Trust warnings (reagent outside calibration range) |
| `error` | `#8E2929` | `#C25555` | Blockers (invalid inputs, simulation failed) |

Badge fill: same hue at 10-14% alpha. Badge text: full saturation. No uppercase forced — the letterspacing carries the chip register.

### Plotly chart palette

Keep the plotly default neutral palette for scientific traces (red / blue / green / orange) — brand gold must not appear inside data plots. Brand gold is reserved for *interactive UI elements around* the plot (axis labels in muted bone/ink, threshold lines, citation chips beneath the figure).

## Spacing

**Two density scales by surface.** Tool surface stays compact (your power users earned it); docs / teaching surface uses editorial rhythm.

- **Base unit:** 4px. All spacing is a multiple of 4px.
- **Tool density:** Compact 4/8/12/16. Reject "generous whitespace" — that's a marketing-site pattern.
- **Docs density:** Editorial 8/16/24/32 with vertical rhythm locked to the body line-height (1.65 × 17px = 28px lead).

| Token | px | Usage |
|---|---|---|
| `space-0.5` | 2 | Inline separators |
| `space-1` | 4 | Tight padding, badge inner padding |
| `space-2` | 8 | Tool widget gap, default gap between inline elements |
| `space-3` | 12 | Tool internal padding |
| `space-4` | 16 | Tool sibling gap |
| `space-6` | 24 | Section subheads (docs) |
| `space-8` | 32 | Top-level sections (docs) |
| `space-12` | 48 | Major structural breaks |

## Layout

- **Approach:** Hybrid by surface, unified by vocabulary. Same border radius, same hairline rule weight, same component padding tokens across all three surfaces.
- **Tool surface:** Three-zone — sidebar nav (~220px) + main (fluid) + evidence inspector rail (~260px). Streamlit columns map directly. Grid-disciplined; never break the gutters.
- **Docs / teaching surface:** Editorial article (~620px reading column) + marginalia rail (~200px) + breakout figure column (~960px when figures need it). TOC sidebar (~220px) on the left.
- **Max content width:** Tool — fluid (scientists want their data table wide). Docs — content column capped at 620px for reading rhythm; figures may break out to 960px.
- **Border radius:** **4px uniform** across all components. No pill buttons, no 16px+ soft-corner cards. Tools, not toys.
- **Elevation:** Minimal. One layer of elevation (surface on background) plus 1px hairline border. **Never** drop shadows — noisy for data UIs and incompatible with the publication register.

## Motion

- **Approach:** Minimal-functional only.
- **Tool surface transitions:** 150ms ease-out on hover and focus state changes. Period.
- **Docs surface single exception:** Citation chips highlight 200ms when their referenced figure scrolls into view. That's the entire motion vocabulary on docs.
- **Forbidden:** Entrance animations, scroll-driven page effects, spring/bouncy curves, page transitions, loading spinners with personality. Every animation is a moment when the user does not know if the result is final — in a simulator, that is a trust leak.

## Component conventions

- **Buttons (primary):** `gold-400` bg (dark) / `gold-600` bg (light), `ink-deep` (dark) / `paper` (light) text, 4px radius, 8px × 16px padding. Hover: `gold-300` / `gold-700`.
- **Buttons (secondary):** transparent bg, primary text, `rule` border. Hover: gold accent border + gold accent text.
- **Buttons (ghost):** transparent bg, muted text, no border. Hover: gold accent text.
- **Inputs:** 1px `rule` border, 4px radius, 8px × 12px padding. Focus: gold accent border + 2px `gold-soft` halo.
- **Evidence badges:** 2px × 8px padding, 2px radius, semantic-color fill at 10-14% alpha + same-color text at 100%. No forced uppercase; letterspacing 0.04em carries the chip register.
- **Metric cards:** 16px padding, surface bg + 1px border, label in Plex Sans 11px uppercase + letterspaced, value in Plex Mono 26-28px tabular-nums, evidence badge inline below the value.
- **Tables (data):** Header in Plex Sans 10-11px uppercase + letterspaced + muted text. Body in Plex Sans 12-13px (numeric cells in Plex Mono with tabular-nums, right-aligned). Zebra striping disabled. Row hover: `gold-soft` background. 1px hairline borders between rows.
- **Citations (docs):** Inline number superscript in gold accent, dotted underline. Marginalia note keyed by the same number in Plex Sans 12px in the right rail.
- **Drop cap (docs only, first paragraph):** Source Serif 4 600 at 60px, float-left, 0.85 line-height, gold accent color.
- **Hairline rule:** 1px `rule` color. Used between top-level sections; never inside a card.
- **Plot frames:** `ink-surface` / `paper-surface` bg, 1px border, 16px padding, plot title in Plex Sans 11px uppercase + letterspaced + muted color above the SVG. Plot SVG axes in muted text color; no gridlines except faint y-axis ticks.

## Accessibility

- **Contrast:** Body text ≥ 7:1 on its surface (AAA). Muted text ≥ 4.5:1 (AA). Verified for both registers.
- **Focus rings:** Always visible. 2px `gold-soft` halo + 1px gold accent border. Never `outline: none` without a replacement.
- **Tabular numerals:** All scientific numeric outputs in Plex Mono with `font-feature-settings: "tnum"`. Decimal alignment is a correctness feature, not a stylistic one.
- **Reduced-motion:** Respect `prefers-reduced-motion`. The 150ms hover and the 200ms citation highlight both gate on this query.

## Implementation entry points (where to look in the codebase)

- Theme injection: `src/dpsim/visualization/app.py` head injection — load Google Fonts `<link>` and inject CSS custom properties from this design.
- Streamlit theme: `.streamlit/config.toml` if it exists, or inline CSS overrides in `app.py`.
- Evidence badge component: search for `compute_min_tier` and `ModelEvidenceTier` to find the rendering points.
- Docs portal (planned): the public docs portal replacing / extending the PDF user manual is the new surface introduced in v10.0; rendering target TBD (likely a separate static-site build under `docs/portal/`).

## Decisions Log

| Date | Decision | Rationale |
|---|---|---|
| 2026-04-18 | v9.0 Industrial-Utilitarian system adopted (Geist Sans + Mono · slate + teal · dark mode primary · 8px compact). | Initial scientific-instrument design system at the end of the v9.0 UI redesign. |
| 2026-05-11 | **v10.0 Research Journal system supersedes v9.0.** Source Serif 4 + IBM Plex Sans + IBM Plex Mono · cream paper + ink + warm gold · two registers (dark tool + light docs) · marginalia rail in docs / teaching. | Two driving signals: (a) v9.0 felt "generic-modern" — interchangeable with any modern data UI, no real point of view; (b) scope expansion to teaching mode (junior-researcher onboarding) and a public docs portal demanded an editorial register the v9.0 system could not carry. The eureka was that DPSim's actual peer set is the scientific publication ecosystem (Distill, Bell Labs, MIT Press), not modern data SaaS — designing it as a *live research journal whose articles happen to compute* fixed the POV problem AND unified all three surfaces (tool, teaching, docs) as the same publication at different depths. Validated against five reference sites (Distill, Quanta, Stripe Press, Stripe Docs, Observable) before commit. |
| 2026-05-11 | Reject Geist; adopt IBM Plex Sans / Mono. | Geist is trending in 2025-26 (Vercel-coded). Plex carries scientific-computing heritage that competitors can't fake by adopting next year's hot font. |
| 2026-05-11 | Replace cool slate + teal with warm cream + ink + gold. | Echoes the printed scientific publication tradition (Stripe Press register but for a tool). Violates the "cool blue/teal = scientific software" cliché — and that's the point. |
| 2026-05-11 | Dark mode primary on tool · light mode primary on docs / teaching. | Lab-running scientists want the dark tool surface (long sessions in dim ambient light). Long-form scientific reading wants the cream-paper light surface. Same palette; different default register by surface. |
| 2026-05-11 | Adopt marginalia rail (Tufte / Distill pattern) for teaching and docs. | Native scientific reading experience. Solves the junior-researcher onboarding problem (commentary lives in the margin without breaking reading flow) without adding a separate "tutorial mode" UI. |
| 2026-05-11 | Evidence-tier hues shifted toward forest / olive / burnt-amber / rust / oxblood (desaturated ~15%). | Reads as printed publication badges, not digital chips. Same `ModelEvidenceTier` enum mapping, just shifted in hue. |
