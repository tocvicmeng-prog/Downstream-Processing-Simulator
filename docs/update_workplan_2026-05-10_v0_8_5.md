# v0.8.5 — M3 real-time back-pressure indicator

> **Joint three-role plan.** /scientific-advisor framing → /architect decomposition → /dev-orchestrator sequenced batches.
>
> Date: 2026-05-10 · Target tag: v0.8.5 · Type: UI-only patch · Backend changes: **none**.

---

## §0 — Reconciliation summary

- v0.8.4 closed 2026-05-10 (tag `v0.8.4`, commit `beacd0c`). 923 tests passing. Audit defects C1–C9 + W-1 + W-2 resolved. UI-completeness reached against the v0.8.3 backend.
- This v0.8.5 patch ships a **single new affordance** — a digital-style real-time back-pressure indicator pinned to the right of the M3 *Live phase view* column diagram, with a `?` glyph that opens an explanation popover.
- **No backend changes.** The `PressureEnvelope` dataclass at `src/dpsim/module3_performance/pressure_envelope.py:97-188` already exposes every quantity the indicator needs: `dP_predicted_pa`, `dP_max_operational_pa`, `headroom_ratio`, `is_warning`, `is_blocker`, `Q_max_m3_s`, `Q_recommended_m3_s`, `decision_tier`, `viscosity`, `valid_domain_violations`.
- Per versioning policy: patch bump to **v0.8.5**; v0.9 stays reserved for matured-status (the three hardware/physics deferrals listed in `HANDOVER_v0_8_4_release.md` §"Open future work").

---

## §1 — /scientific-advisor framing — what the indicator MUST mean

### 1.1 What is being read
The displayed value is the **bed-axial pressure drop ΔP across the packed bed at the current volumetric flow rate Q**. In an offline replay this comes from the latest CSV reading (`tab_m3_monitor.py`); in the static pre-flight view it falls back to `envelope.dP_predicted_pa` — the Kozeny-Carman prediction at `Q_set` under the resolved μ and column geometry.

### 1.2 What "safe" means — the ceiling
The operational ceiling is `envelope.dP_max_operational_pa`, derived per **ADR-004** from the per-family bed-compression limit:

> u_crit ≈ K_geom · G_DN · d_p² / (μ · L)
>
> ΔP_max,op = 150 · μ · u_crit · L · (1−ε)² / (ε³ · d_p²) + ΔP_frit

Exceeding this causes **irreversible bed compression**. The structural ceiling `dP_max_burst_pa` (from E_star) is a separate, much higher bound and must **not** be the indicator's reference colour, even though using it would keep the indicator green for longer. The operator-facing safe limit is the operational ceiling.

### 1.3 Three-band colour semantic
Mirrors the existing `_STATE_COLORS` palette already in use at `tab_m3_monitor.py:42-46` — no new colour tokens introduced.

| Band | Condition | Colour | Token | Operator interpretation |
|---|---|---|---|---|
| GREEN | `headroom_ratio` < 0.70 | `#10B981` | `green-500` | Comfortable cruise — ≥ 30 % headroom |
| AMBER | 0.70 ≤ `headroom_ratio` < 1.00 | `#F59E0B` | `amber-500` | Approaching ceiling — start preventive action |
| RED | `headroom_ratio` ≥ 1.00 | `#EF4444` | `red-500` | Ceiling exceeded — immediate action required |

Where `headroom_ratio = ΔP_current / ΔP_max_operational` (analogous to `PressureEnvelope.headroom_ratio` at `pressure_envelope.py:166-177`, but driven by the *measured* ΔP, not the *Q* ratio).

### 1.4 Remediation actions surfaced by the `?` popover
Ordered by reversibility — operator should try them in this order. This mirrors the `RecoveryAction` enum already surfaced in `tab_m3_monitor.py:50-58`.

1. **Lower Q to `envelope.Q_recommended_m3_s`** — restores ~50 % headroom by definition (`Q_recommended = 0.5 · Q_max`). First action; fully reversible.
2. **Switch to wash buffer** — reduces μ via mobile-phase change; only useful when fouling is suspected.
3. **Stop flow and repack column** — when a clogged frit or channelled bed is suspected.
4. **Emergency stop** — when dΔP/dt rises faster than the rate threshold (bed about to compress).

### 1.5 Decision-tier honesty
The popover MUST NOT promise predictive accuracy beyond the active `envelope.decision_tier`. At SEMI_QUANTITATIVE the safe-limit value carries a ±50 % / ×2 interval per `_INTERVAL_FACTOR_BY_TIER` at `pressure_envelope.py:196-202`. The popover surfaces this interval explicitly so the operator never reads a single number as a hard truth at SEMI_QUANTITATIVE.

---

## §2 — /architect framing — module decomposition + integration

### 2.1 Six-dimension verdict on doing this inline in `tab_m3.py:211-233`

| Dimension | Verdict | Diagnosis |
|---|---|---|
| Correctness | PASS | The envelope already carries the right fields. |
| Completeness | **FAIL** | No real-time reading surfaced next to the diagram today (the live-phase block is purely the cross-section animation). |
| Modularity | **FAIL** | Inlining ~140 LOC of indicator logic into a 1198-line file violates the v0.8.4 decomposition principle. |
| Scalability | PASS | Single component; no fan-out. |
| Maintainability | **PARTIAL** | Inline rendering is hard to test against a stub container. |
| Scientific provenance | **PARTIAL** | `decision_tier` and `valid_domain_violations` need to thread through into the popover. |

→ **Verdict: extract into a new component module.**

### 2.2 Module decomposition

| File | Status | LOC budget | Responsibility |
|---|---|---|---|
| `src/dpsim/visualization/components/pressure_indicator.py` | NEW | ~140 | Digital-style readout + band colourer + popover content composer |
| `src/dpsim/visualization/components/assets/pressure_indicator.html` | NEW | ~80 | Embedded SVG/HTML template (Geist Mono digital glyphs, `?` glyph anchor) |
| `tests/visualization/test_pressure_indicator.py` | NEW | ~120 | Band-threshold unit tests + envelope-missing fallback + popover-content composition |
| `src/dpsim/visualization/tabs/tab_m3.py:211-233` | EDITED | +6 / −0 | Wrap `render_column_xsec` in `st.columns([3, 1])`, render indicator into the right column |
| `src/dpsim/visualization/components/__init__.py` | EDITED | +2 | Export `render_pressure_indicator` |

### 2.3 Signature contract

```python
from __future__ import annotations
from typing import Any, Literal, Optional

from dpsim.module3_performance.pressure_envelope import PressureEnvelope


_Band = Literal["green", "amber", "red"]


def render_pressure_indicator(
    *,
    envelope: Optional[PressureEnvelope],
    current_dp_pa: Optional[float] = None,
    container: Any = None,
    width_px: int = 220,
    height_px: int = 360,
) -> None:
    """Render the digital-style back-pressure indicator.

    Args:
        envelope: The active step's pre-flight envelope. None when no run
            has been computed yet — the indicator renders a labelled
            placeholder ("envelope not yet computed") in this case.
        current_dp_pa: The latest measured ΔP from the streaming monitor
            (None during the static pre-flight view; set by the offline
            replay path). When None, falls back to
            envelope.dP_predicted_pa.
        container: Streamlit container; defaults to st itself.
        width_px / height_px: Sized to align vertically with the
            adjacent column_xsec (default 360px height matches
            column_xsec's _DEFAULT_HEIGHT).
    """


def _band(headroom_ratio: float) -> _Band:
    """Pure mapping: < 0.70 → green, < 1.00 → amber, else red."""


def _help_modal_html(envelope: PressureEnvelope) -> str:
    """Compose the popover body. Surfaces:
    - dP_max_operational at current decision_tier with the
      tier-aware interval bracket.
    - The u_crit · K_geom · G_DN · d_p² / (μ · L) calculation summary.
    - The four ranked remediation actions from §1.4.
    - The decision_tier banner phrasing from the README guardrail.
    """
```

### 2.4 Integration seam — `tab_m3.py:211-233`

```python
# Before (current at v0.8.4):
from dpsim.visualization.components import render_column_xsec
...
render_column_xsec(
    phase=_phase,
    column_length_mm=float(bed_height_cm * 10),
    column_diameter_mm=float(col_diam_mm),
)

# After (v0.8.5):
from dpsim.visualization.components import (
    render_column_xsec,
    render_pressure_indicator,
)
...
_col_xsec, _col_indicator = st.columns([3, 1], gap="small")
with _col_xsec:
    render_column_xsec(
        phase=_phase,
        column_length_mm=float(bed_height_cm * 10),
        column_diameter_mm=float(col_diam_mm),
    )
with _col_indicator:
    render_pressure_indicator(
        envelope=st.session_state.get("m3_pressure_envelope"),
        current_dp_pa=st.session_state.get("m3_latest_dp_pa"),
    )
```

### 2.5 State management

- Read keys (no new writers from this feature):
  - `st.session_state["m3_pressure_envelope"]` — written by the existing pre-flight envelope panel (B-2h).
  - `st.session_state["m3_latest_dp_pa"]` — written by the offline replay path **after this batch lands**; until then `current_dp_pa` is None and the static fallback (`envelope.dP_predicted_pa`) drives the colour.
- The `?` popover state lives entirely inside `st.popover`; no session_state plumbing needed.

### 2.6 DESIGN.md compliance

- **Typography**: Geist Mono 700 / 28 px for the value (per DESIGN.md §"Typography" — *"Data / tables / metrics: Geist Mono 400 14 px"* and §"Component conventions" — *"Metric cards: large number in Geist Mono 700 at 28 px"*). Tabular numerals enabled via `font-feature-settings: "tnum"`.
- **Palette**: only the three semantic colours `#10B981` / `#F59E0B` / `#EF4444` already in use elsewhere. No new tokens.
- **Surface**: `slate-100` (light) / `slate-800` (dark) background, 1 px `slate-200` / `slate-700` border, **4 px** uniform border radius.
- **No** drop shadow, **no** entrance animation, **no** gradient — per DESIGN.md §"Layout" and §"Motion".
- **Allowed motion**: 150 ms ease-out colour transition on band change (within the §"Motion" allowance for hover/focus state changes).

### 2.7 Tier-policy plumbing

The indicator is a *measurement*, not a model output. The displayed number reads either a measured ΔP (offline replay) or the model's `dP_predicted_pa` (static fallback). In both cases the SEMI_QUANTITATIVE banner (`shell/tier_banner.py`, W-058) already surfaces the active tier at every stage. The popover surfaces the per-tier interval bracket inline so the operator can see ±50 % / ×2 framing for a SEMI_QUANTITATIVE ceiling. **No new `OutputType` member required.**

### 2.8 v9.0 Family-First contract + AST gate

- The indicator does not branch on `PolymerFamily`. Family-aware K_geom resolution already happened upstream when the envelope was computed.
- No new `is` / `is not` enum-comparison risks introduced.

### 2.9 Forward audit — predicted post-implementation verdict

| Dimension | Predicted | Residual gap |
|---|---|---|
| Correctness | PASS | — |
| Completeness | PASS | Live AKTA UNICORN feed still v0.9 (ADR-008) |
| Modularity | PASS | — |
| Scalability | PASS | — |
| Maintainability | PASS | — |
| Scientific provenance | PASS | — |

---

## §3 — /dev-orchestrator framing — work plan

### 3.1 Work-item ledger (continues from W-063)

| W-ID | Bundle | Severity | Title | Files | Resolves |
|---|---|---|---|---|---|
| W-064 | A | MEDIUM | Pressure indicator component | NEW `components/pressure_indicator.py` + `assets/pressure_indicator.html` | new feature |
| W-065 | A | LOW | Help-modal content + `?` popover wiring | `components/pressure_indicator.py` | sub-task of W-064 |
| W-066 | A | MEDIUM | M3 Live-phase 2-column layout + integration | `tabs/tab_m3.py:211-233` | new feature |
| W-067 | B | LOW | Live-reading `session_state` read-through | `components/pressure_indicator.py` + `tabs/tab_m3_monitor.py` (writer side) | new feature |
| W-068 | C | LOW | Test suite + DESIGN.md compliance | NEW `tests/visualization/test_pressure_indicator.py` | gate-39, gate-40, gate-41 |

### 3.2 Sequenced batched plan

| Batch | W-IDs | Modules touched | Model | Acceptance criteria |
|---|---|---|---|---|
| **B-3a** | W-064, W-065 | `components/pressure_indicator.py` + asset HTML + `components/__init__.py` | Sonnet | `_band` returns correct band at the three boundary values (0.69, 0.70, 1.00, 1.01); `_help_modal_html` includes (a) `dP_max_operational_pa` with tier-aware interval bracket, (b) the u_crit formula text, (c) all four ranked remediations from §1.4. |
| **B-3b** | W-066 | `tabs/tab_m3.py:211-233` | Sonnet | Visually-verified: column diagram and indicator vertically centred, indicator at 25 % column width. Existing `m3_xsec_phase` radio still works. |
| **B-3c** | W-067 | `components/pressure_indicator.py` + `tabs/tab_m3_monitor.py` writer | Sonnet | Indicator picks up `m3_latest_dp_pa` when offline replay is active; falls back to `dP_predicted_pa` otherwise. |
| **B-3d** | W-068 | NEW `tests/visualization/test_pressure_indicator.py` | Sonnet | ≥ 8 tests: band boundaries × 3, missing envelope, decision_tier passthrough, popover-content composition × 2, integration smoke via `_StubContainer`. ruff + mypy clean. |
| **B-4a** | release | `pyproject.toml` + `__init__.py` + `CHANGELOG.md` + NEW `docs/handover/HANDOVER_v0_8_5_release.md` | Haiku | Version bump 0.8.4 → 0.8.5; CHANGELOG entry; release handover; tag `v0.8.5`. |

### 3.3 Token-economy + checkpoints

- **Total estimated context**: ≈ 12 K tokens across all batches. **Single-session feasible** at GREEN context budget.
- **No mid-cycle compression** required.
- **No milestone handover** within the cycle (single feature).
- **`/qa-only`** invocation between B-3c and B-3d to sanity-check the live-reading hook before tests are written.
- **`/design-review`** invocation against the rendered indicator to verify DESIGN.md compliance (Geist Mono, semantic colours, no shadow/gradient/entrance-animation).

### 3.4 Validation gates added (38 → 41) on top of the v0.8.4 gate floor

| Gate | Description |
|---|---|
| **38** | Indicator renders to the right of the column diagram in M3 Live-phase view; vertically centred at the column's geometric midline. |
| **39** | Value text colour matches band: GREEN at `headroom_ratio` < 0.70; AMBER at 0.70 ≤ ratio < 1.00; RED at ratio ≥ 1.00. |
| **40** | `?` popover surfaces (a) `dP_max_operational` with tier-aware interval, (b) the K_geom · G_DN · d_p² / (μ · L) calculation summary, (c) the four ranked remediations starting with "lower Q to Q_recommended". |
| **41** | When `m3_pressure_envelope` is absent from session_state (first load), the indicator renders a clearly-labelled placeholder ("envelope not yet computed") — never a misleading 0 / NaN / dash. |

### 3.5 Definition of "v0.8.5 ships"

> v0.8.5 ships when gates 1 → 41 pass. The README's "screen → calibrate → tighten" promise is unchanged from v0.8.4; this release upgrades the *operator-facing situational awareness* during live operation.

### 3.6 Out of scope (explicitly deferred)

- **Live AKTA UNICORN socket** — still v0.9 (ADR-008, hardware-bound).
- **Continuous polling animation** — Streamlit doesn't support per-component timers cheaply; the indicator updates on rerun, which is what the offline-replay path drives anyway.
- **Audible / push-notification alerts on RED** — visual band is the contract; no audio scope creep.
- **Mobile-phase μ recompute on indicator change** — μ is owned upstream by the mobile-phase widget (W-053).
- **Cyclic SMB / multi-column dashboards** — all v0.9 deferrals are unchanged from v0.8.4.

---

## §4 — Module registry (initial)

| Module | Status | Tier | Owner | Linked W-items |
|---|---|---|---|---|
| `components/pressure_indicator.py` | NOT STARTED | n/a | architect | W-064, W-065, W-067 |
| `components/assets/pressure_indicator.html` | NOT STARTED | n/a | architect | W-064 |
| `tests/visualization/test_pressure_indicator.py` | NOT STARTED | n/a | scientific-coder | W-068 |

---

## §5 — Handover targets

- `docs/handover/HANDOVER_v0_8_5_pressure_indicator.md` — combined batch handover for B-3a → B-3d.
- `docs/handover/HANDOVER_v0_8_5_release.md` — release-level close (mirrors the v0.8.4 release handover format).

---

## §6 — Executive summary (≤ 80 words)

v0.8.5 adds a digital-style real-time back-pressure indicator pinned to the right of the M3 column diagram. It reads from the existing `PressureEnvelope` dataclass — **no backend changes**. The number turns green / amber / red against `dP_max_operational_pa`; a `?` popover explains the calculation and the four ranked remediations starting with *lower Q to Q_recommended*. Five W-items (W-064 → W-068) sequenced into 4 small Sonnet batches + 1 Haiku release batch; ≈ 12 K token budget; no mid-cycle handover.
