# Architecture — DPSim v0.8.3 → v0.8.4 UI upgrade decomposition

**Phase 2 of joint engagement** — `/architect`. Consumes Phase 1 (`AUDIT_v0_8_3_ui_completeness.md`) verbatim. Phase 3 (`/dev-orchestrator`) consumes this document verbatim.
**Date:** 2026-05-10
**Backend baseline:** v0.8.3 (no backend changes required for this UI work)
**Defect catalogue inherited:** C1–C9, W-1, W-2 (Phase 1 §6).

---

## §1 Six-dimension audit verdict on the existing visualization surface

| # | Dimension | Verdict | Concrete evidence | Diagnosis |
|---|---|---|---|---|
| D1 | **Correctness** | **PASS** | `max_safe_flow_rate` cleanly removed (`plots_m3.py:663` is a docstring deprecation note only); render_metric correctly tier-gates M1/M2/M3 scalars; pre-flight envelope wires the right `compute_pressure_envelope` signature at `tabs/tab_m3.py:1005`. | The UI does not lie about what it computes. The defects are omissions, not falsehoods. |
| D2 | **Completeness** | **FAIL** | C1–C7, C9. 14 backend capabilities classified MISSING-in-UI (Phase 1 §3). The forward MC, inverse Bayesian, multi-column series, salt/imidazole-modulated isotherm selection, and mobile-phase composition input are all unreachable. | The UI exposes ~1/3 of the v0.7 → v0.8.3 user-facing surface. This is the defining gap of the upgrade. |
| D3 | **Modularity** | **PARTIAL** | `tab_m3.py` is 1198 LOC and growing — adding 4 more sections inline would push it beyond 2000 LOC. `panels/calibration.py:42` and `shell/stage_panels.py:387` host two unrelated unlabelled file uploaders (C6). `decision_grade_render.py` is a clean shared helper but not all callers consume it. | The shared-helper pattern (`render_metric`, `render_decision_grade_annotation`) is right; placement of the larger uncertainty/calibration features needs explicit module boundaries. **No re-architecture required**, but new top-level tab boundary is needed. |
| D4 | **Scalability** | **PASS** | The Streamlit reload model + session_state pattern handles arbitrary panel additions; the app.py shell is lean (~700 LOC); decision_grade policy is registry-driven. | Adding new tabs / sections is a low-risk additive change. |
| D5 | **Maintainability** | **PARTIAL** | Two-uploader confusion (C6) makes calibration ingestion non-obvious; `plots_m2.py` "Trust:" badge (C8) is a parallel mechanism duplicating decision-grade gating; isotherm selection at `tab_m3.py:360–377` hardcodes Langmuir → users cannot follow the v0.8.x literature path through the UI. | Fragmentation, not architecture rot. Localised cleanups + one tab split. |
| D6 | **Scientific provenance** | **FAIL** | C1 (mobile-phase compositional inputs absent ⇒ ADR-005 elution physics not reachable from UI); C3 (`p_blocker` advisory unreachable ⇒ ADR-007 wet-lab risk story breaks); C4 (inverse inference unreachable ⇒ ADR-010 calibration handshake breaks); W-1 (no SEMI_QUANTITATIVE INTERVAL banner ⇒ CHANGELOG framing not visible). | The UI describes `SEMI_QUANTITATIVE INTERVAL` outputs without surfacing the calibration handshake that promotes them. Resolves with C1+C3+C4+C6+W-1 fixes. |

**Aggregate verdict:** **REVISION REQUIRED**. The visualization surface is architecturally sound (D1, D4 PASS). Two dimensions FAIL on completeness/provenance grounds (D2, D6) and two are PARTIAL on modularity/maintainability grounds (D3, D5). **No `[REDESIGN]` tags applied.** The fixes are an additive build-out plus one tab split, not a re-architecture.

---

## §2 Module decomposition

### Central decision — new top-level tab, not inline `tab_m3.py` extension

`tab_m3.py` is 1198 LOC and serves a coherent narrative: *configure column → run breakthrough → review pre-flight envelope → review streaming monitor*. The MC/inverse/multi-column work is a **second narrative** — *run uncertainty analysis on the deterministic result* — that flows from the M3 tab's output. Inlining would conflate two flows in one file beyond 2000 LOC. **Decision: a NEW top-level tab `tab_calibration.py` (~700 LOC budget) hosts forward MC, inverse inference, multi-column series builder, and calibration-store ingestion in four sub-sections.** The shared widgets (mobile phase, isotherm selector) live under `panels/` since both `tab_m3.py` and `tab_calibration.py` consume them.

### File placement table

| New file | Parent surface | Responsibility | LOC budget | Why this placement |
|---|---|---|---|---|
| `src/dpsim/visualization/panels/mobile_phase.py` | shared | Mobile-phase composition widget (C1) | 90 | Consumed by `tab_m3.py` (pre-flight envelope) AND `tab_calibration.py` (forward MC, inverse). Shared = one source of truth. |
| `src/dpsim/visualization/panels/isotherm_selector.py` | shared | Isotherm dropdown + family-aware default + parameter sub-form (C2) | 220 | Five isotherm classes need coherent presentation; the parameter set differs per class. Shared because gradient-elution and breakthrough panels both need it. |
| `src/dpsim/visualization/tabs/tab_calibration.py` | NEW top-level tab | Hosts the four sub-sections — forward MC, inverse inference, multi-column series, calibration-store ingestion (C3, C4, C5, C6) | 700 | Thematically distinct from `tab_m3.py`'s deterministic flow; LOC budget for `tab_m3.py` would otherwise blow out. |
| `src/dpsim/visualization/tabs/calibration/forward_mc.py` | sub-section of `tab_calibration` | `monte_carlo_pressure_envelope` runner + `p_blocker` advisory (C3) | 180 | One per concern; sub-section split keeps `tab_calibration.py` itself a thin dispatcher. |
| `src/dpsim/visualization/tabs/calibration/inverse_inference.py` | sub-section of `tab_calibration` | `infer_posterior_envelope` runner + measurement editor + ESS chip + round-trip button (C4) | 220 | Largest sub-section; isolating keeps it auditable. |
| `src/dpsim/visualization/tabs/calibration/multi_column.py` | sub-section of `tab_calibration` | `MultiColumnGeometry` builder + `compute_multi_column_envelope` runner + per-column display (C5) | 200 | Series-geometry concept is its own sub-narrative. |
| `src/dpsim/visualization/tabs/calibration/wetlab_ingestion.py` | sub-section of `tab_calibration` | YAML upload via `calibration.wetlab_ingestion` + tier-promotion preview (C6) | 130 | Replaces the unlabelled `panels/calibration.py:42` uploader; the latter file is repurposed as an alias re-export for backwards-compat or removed. |
| `src/dpsim/visualization/shell/tier_banner.py` | new shell component | Top-of-page SEMI_QUANTITATIVE banner (W-1) | 80 | Visible across every tab; lives in shell because it gates global reading of the dashboard. |
| `src/dpsim/visualization/components/next_step_affordance.py` | new component | Post-lifecycle "what's next" 3-button strip (W-2) | 70 | Consumed at end of `tab_m3.py` only; isolated for testability. |

### Files modified in place (no new files)

| File | Modification | Defect resolved |
|---|---|---|
| `src/dpsim/visualization/plots_m2.py` | Add `tier=` kwarg to `plot_surface_area_comparison`; route the "Trust:" annotation through `render_decision_grade_annotation`. Mirrors W-035 / W-037. | C8 |
| `src/dpsim/visualization/tabs/tab_m3_monitor.py` | Extend `render_pressure_monitor_section` with a per-rule `RecoveryAction` timeline ribbon under the existing status panel. | C9 |
| `src/dpsim/visualization/tabs/tab_m3.py` | Replace the hardcoded q_max/K_L sliders at lines 360–377 with `render_isotherm_widget`. Insert `render_mobile_phase_widget` near the column-geometry inputs. Insert `render_next_step_affordance` after the breakthrough panel. | C1, C2, W-2 |
| `src/dpsim/visualization/app.py` | Insert `tier_banner` at top of every stage; add `tab_calibration` as a peer top-level tab; expose new session_state keys. | W-1, plus tab-mounting for tab_calibration |
| `src/dpsim/core/decision_grade.py` | Add three new `OutputType` members: `MC_PROBABILITY`, `POSTERIOR_PARAMETER`, `ESS`. Add policy rows. Mirrors v0.7 W-030. | (cross-cutting; needed by C3, C4) |

---

## §3 Signature contracts

All signatures use full Python typing. All widgets accept a Streamlit container kwarg (`container=None` defaults to `st`). Widget keys are namespaced via a `key_prefix: str` argument so the same widget can render twice on different tabs without state collisions.

### 3(a) Mobile-phase composition widget — resolves C1

```python
# src/dpsim/visualization/panels/mobile_phase.py
def render_mobile_phase_widget(
    *,
    container: Any = None,
    key_prefix: str = "mp",
    initial: Optional[MobilePhase] = None,
    show_extrapolation_warning: bool = True,
) -> MobilePhase:
    """Render a 5-field mobile-phase composition editor.

    Fields:
      - T_C            slider 0–80 °C, default 25 (water-T table domain)
      - c_nacl_M       slider 0.0–0.5 M, default 0.15 (PBS reference)
      - phi_glycerol   slider 0.0–0.5, default 0.0 (additive-model domain)
      - phi_ethanol    slider 0.0–0.5, default 0.0 (additive-model domain)
      - custom_mu_pa_s number input, optional override toggle
    On user-set μ override the widget tags the returned MobilePhase
    so downstream consumers can promote viscosity tier to CALIBRATED_LOCAL.
    """
```

**Why:** ADR-005 §"Why ν = 4.5" + ADR-007 §"prior choices" both depend on a meaningful (T, c_NaCl, glycerol, ethanol) state. The slider domains mirror the v0.7 viscosity model's `valid_domain` exactly so the widget cannot generate inputs the model rejects.

### 3(b) Isotherm selector + parameter editor — resolves C2

```python
# src/dpsim/visualization/panels/isotherm_selector.py
class IsothermChoice(Enum):
    LANGMUIR = "langmuir"
    SALT_MODULATED_LANGMUIR = "salt_modulated_langmuir"
    IMIDAZOLE_MODULATED_LANGMUIR = "imidazole_modulated_langmuir"
    SALT_MODULATED_SMA = "salt_modulated_sma"
    SALT_MODULATED_COMPETITIVE_LANGMUIR = "salt_modulated_competitive_langmuir"

@dataclass(frozen=True)
class IsothermSpec:
    choice: IsothermChoice
    params: dict[str, Any]                 # parameter dict for the chosen class
    estimated_tier: ModelEvidenceTier      # SEMI_QUANTITATIVE by default;
                                           # CALIBRATED_LOCAL when user flags it

def render_isotherm_widget(
    *,
    container: Any = None,
    key_prefix: str = "iso",
    polymer_family: PolymerFamily,
    binding_model_hint: Optional[str] = None,   # from FunctionalMediaContract
    initial: Optional[IsothermSpec] = None,
) -> IsothermSpec:
    """Family-aware isotherm dropdown with conditional parameter sub-form.

    Default selection logic (v9.0 Family-First):
      - binding_model_hint=="protein_a"  → LANGMUIR (no salt physics relevant)
      - binding_model_hint=="iex_*"      → SALT_MODULATED_LANGMUIR
      - binding_model_hint=="imac"       → IMIDAZOLE_MODULATED_LANGMUIR
      - binding_model_hint=="hic"        → LANGMUIR (HIC has its own physics; v0.9 candidate)
      - else                             → LANGMUIR

    The parameter sub-form is rendered conditionally on choice.value
    (NEVER `is`; AST gate). 'calibrated_locally' checkbox routes the
    estimated_tier to CALIBRATED_LOCAL when the user has fitted nu / n
    locally.
    """
```

**Why:** Family-First contract dictates that the family + the M2 binding hint together drive the default. Conditional parameter sub-form prevents the user from filling fields that don't apply to their chosen class.

### 3(c) Forward MC envelope panel — resolves C3

```python
# src/dpsim/visualization/tabs/calibration/forward_mc.py
@dataclass(frozen=True)
class ForwardMCRunInputs:
    polymer_family: PolymerFamily
    column: ColumnGeometry
    mobile_phase: MobilePhase
    Q_set_m3_s: float
    n_samples: int = 500
    seed: int = 42
    use_family_priors: bool = False
    log_cov: Optional[np.ndarray] = None     # populated by inverse-tab round-trip

def render_forward_mc_panel(
    *,
    container: Any = None,
    key_prefix: str = "fmc",
    inputs: ForwardMCRunInputs,
) -> Optional[MCEnvelopeBands]:
    """Renders the forward-MC sub-section of tab_calibration.

    Controls: n_samples slider (50–5000), seed input, prior mode radio
    [literature default | family priors | custom σ_log_*], correlated-prior
    toggle (consumes inputs.log_cov when present from inverse round-trip).

    Run button → monte_carlo_pressure_envelope. Result panel:
      - P05/P50/P95 bands (Q_max, ΔP_predicted, headroom_ratio) via render_metric
      - p_blocker chip (RED above 0.05, AMBER 0.01–0.05, GREEN below)
      - p_warning chip
      - 'Drop Q to Q_recommended' callout when p_blocker > 0.05

    Stores result on st.session_state['forward_mc_bands'].
    """
```

**Why:** The README's central advisory ("treat `p_blocker > 0.05` as a strong signal") only works if the UI surfaces the threshold ladder visually. Three-band chip mirrors the streaming-monitor state-chip language so users learn one visual vocabulary.

### 3(d) Inverse inference panel — resolves C4

```python
# src/dpsim/visualization/tabs/calibration/inverse_inference.py
def render_inverse_inference_panel(
    *,
    container: Any = None,
    key_prefix: str = "inv",
    polymer_family: PolymerFamily,
    column: ColumnGeometry,
    mobile_phase: MobilePhase,
    Q_for_envelope: float,
) -> Optional[InferredPosteriorEnvelope]:
    """Inverse Bayesian inference panel with measurement editor.

    Sections:
      1. Measurement table — st.data_editor over MeasuredPressureFlowPoint
         columns (Q_m3_s, dP_pa, sigma_dP_pa). Add/remove rows; CSV import
         button.
      2. Run controls — n_samples (100–5000), seed.
      3. Run button → infer_posterior_envelope.
      4. ESS diagnostic — render_metric with new OutputType.ESS;
         ess_warning surfaced as st.warning() block when present.
      5. Posterior bands — render_metric for K_geom_p05/p50/p95,
         mu_p05/p50/p95, G_DN_p05/p50/p95 with new OutputType.POSTERIOR_PARAMETER.
      6. Round-trip button — writes posterior log_cov to
         st.session_state['posterior_log_cov']; the forward-MC panel
         picks it up via ForwardMCRunInputs.log_cov.

    Stores result on st.session_state['posterior_envelope'].
    """
```

**Why:** ADR-010 §"Tier mapping" requires that the inverse output stays SEMI_QUANTITATIVE; the round-trip step is what closes the wet-lab handshake. A separate button keeps the round-trip explicit (auditable) rather than automatic.

### 3(e) Multi-column series builder — resolves C5

```python
# src/dpsim/visualization/tabs/calibration/multi_column.py
def render_multi_column_builder(
    *,
    container: Any = None,
    key_prefix: str = "mcg",
    default_geometry: ColumnGeometry,
    default_family: PolymerFamily,
    mobile_phase: MobilePhase,
    Q_set_m3_s: float,
) -> Optional[MultiColumnPressureEnvelope]:
    """Series-of-columns builder + envelope runner.

    Per-row inputs (st.data_editor):
      - polymer_family selector
      - diameter_m
      - bed_height_m
      - bed_porosity
      - particle_porosity
      - G_DN_pa_override (optional)
      - E_star_pa_override (optional)
      - bead_d32_m_override (optional)

    Default rows: capture (bed_height=0.05) + polish (bed_height=0.10).
    Add/remove buttons. Run → compute_multi_column_envelope.
    Result: per-column envelopes table + series_Q_max/headroom/decision_tier.
    Bottleneck column highlighted in the per-column table.
    """
```

**Why:** ADR-009 series scope explicitly. Bottleneck column highlight makes the worst-step verdict immediately legible (mirrors the streaming monitor's first-blocker anchor).

### 3(f) Calibration-store ingestion panel — resolves C6

```python
# src/dpsim/visualization/tabs/calibration/wetlab_ingestion.py
@dataclass(frozen=True)
class IngestionDiff:
    promoted_outputs: list[tuple[str, ModelEvidenceTier, ModelEvidenceTier]]
    # (output_name, before_tier, after_tier)
    family_kgeom_changes: dict[PolymerFamily, tuple[float, float]]
    # family → (before_K_geom, after_K_geom)

def render_calibration_ingestion_panel(
    *,
    container: Any = None,
    key_prefix: str = "cal",
    calibration_store: Any,                  # CalibrationStore
) -> Optional[IngestionDiff]:
    """Wet-lab YAML upload (clearly labelled).

    Sections:
      1. Header explaining what wetlab_ingestion does + link to
         data/wetlab_calibration_examples/
      2. Single labelled file_uploader 'Upload wet-lab calibration campaign (YAML)'
      3. Validation summary — row count, fields detected, schema errors
      4. Tier-promotion preview — for each affected output, show
         before_tier → after_tier diff with arrows.
      5. Confirm button writes to calibration_store + emits an
         on-screen success notice.
    """
```

**Why:** C6's two-uploader confusion resolves by deleting the unlabelled `panels/calibration.py:42` widget and consolidating here. Tier-promotion preview is the user-visible promise of the wet-lab loop.

### 3(g) RecoveryAction timeline — resolves C9

```python
# Modification to src/dpsim/visualization/tabs/tab_m3_monitor.py
def _render_recovery_action_timeline(
    *,
    container: Any,
    summary: ReplaySummary,
) -> None:
    """Per-reading state-chip + action-chip ribbon.

    For each reading in summary.state_timeline, render a small chip
    coloured by state (existing _STATE_COLORS) with the RecoveryAction
    label below it (existing _RECOVERY_ACTION_LABEL). Hover-text shows
    triggered_rule.value.
    """
```

**Why:** The streaming monitor already has the state timeline data; the action label is in the same `_RULE_TO_ACTION` registry. This is a presentation-only extension.

### 3(h) plots_m2.py tier-gating — resolves C8

```python
# Modification to src/dpsim/visualization/plots_m2.py
def plot_surface_area_comparison(
    surface_model: Any,
    *,
    tier: Optional[ModelEvidenceTier] = None,    # NEW
) -> Optional[object]:
    """tier kwarg routes the existing 'Trust:' badge through
    render_decision_grade_annotation. tier=None preserves legacy."""
```

**Why:** Direct mirror of W-035 / W-037; one new kwarg + branch on `tier is not None`.

### 3(i) Top-of-page SEMI_QUANTITATIVE banner — resolves W-1

```python
# src/dpsim/visualization/shell/tier_banner.py
def render_tier_banner(
    *,
    container: Any = None,
    weakest_tier: ModelEvidenceTier,
    has_calibration: bool,
) -> None:
    """Persistent banner at the top of every stage.

    Three states (semantic colours per DESIGN.md):
      - GREEN — calibrated_local or higher AND has_calibration is True
      - AMBER — semi_quantitative (the default state)
      - RED   — qualitative_trend or unsupported

    Banner text: 'DPSim outputs are <TIER> until calibration is loaded.
    Do not describe results as "validated" without wet-lab handshake.'
    """
```

**Why:** The README guardrail ("do not describe DPSim as 'validated' unless calibration_store carries justifying data") needs to be visible at every stage, not buried.

### 3(j) "What's next" affordance — resolves W-2

```python
# src/dpsim/visualization/components/next_step_affordance.py
def render_next_step_affordance(
    *,
    container: Any = None,
    lifecycle_result: DownstreamLifecycleResult,
) -> None:
    """Three-button strip after lifecycle completes.

    Each button toggles a session_state flag the calibration tab
    consumes:
      [Run forward MC]      → ss['_jump_to_calibration_section'] = 'forward_mc'
      [Fit posterior K_geom] → ss['_jump_to_calibration_section'] = 'inverse'
      [Build series geometry] → ss['_jump_to_calibration_section'] = 'multi_column'

    The calibration tab opens its corresponding sub-section on first
    render after the flag is set.
    """
```

---

## §4 Integration-seam map

| Component (§3) | File:line | Wire-in |
|---|---|---|
| 3(a) mobile_phase | `tabs/tab_m3.py` insert near line 320 (column geometry section) | New widget instance; bound to `st.session_state['mobile_phase']`. Pre-flight envelope (`tab_m3.py:1005`) reads from session_state instead of hardcoded `MobilePhase()`. |
| 3(a) mobile_phase | `tabs/calibration/forward_mc.py`, `inverse_inference.py`, `multi_column.py` | All three consume `st.session_state['mobile_phase']` (single source of truth). |
| 3(a) mobile_phase | `lifecycle/orchestrator.py:781` (existing `MobilePhase()` literal) | **Backend change** — the orchestrator's pre-flight envelope call should accept a MobilePhase override; UI passes `st.session_state['mobile_phase']` through the recipe. |
| 3(b) isotherm_selector | `tabs/tab_m3.py:360–377` | Replace hardcoded q_max + K_L sliders with `render_isotherm_widget`. Result `IsothermSpec` is consumed by `run_breakthrough` + `run_gradient_elution`. |
| 3(c) forward_mc | `tabs/tab_calibration.py` sub-section dispatcher | First sub-tab. Consumes `st.session_state['forward_mc_bands']` for chart/metric display. |
| 3(d) inverse_inference | `tabs/tab_calibration.py` sub-section dispatcher | Second sub-tab. Writes `st.session_state['posterior_envelope']` and `st.session_state['posterior_log_cov']`. |
| 3(e) multi_column | `tabs/tab_calibration.py` sub-section dispatcher | Third sub-tab. |
| 3(f) wetlab_ingestion | `tabs/tab_calibration.py` sub-section dispatcher | Fourth sub-tab. **Deletes the unlabelled uploader at `panels/calibration.py:42`.** Reads / writes `st.session_state['_cal_store']` (existing key from `ui_workflow.py:881`). |
| 3(g) RecoveryAction timeline | `tabs/tab_m3_monitor.py:240+` | Inserted into the existing replay-result panel after the trace plot. |
| 3(h) plots_m2 tier wire | `plots_m2.py:130` (function signature) + `:144` (annotation site) | Add `tier` kwarg + conditional `render_decision_grade_annotation` branch. |
| 3(i) tier_banner | `app.py` top of every stage (`_render_stage` at line 506) | Banner is the first child of the stage container. Reads `st.session_state['_lifecycle_result']` for the weakest tier. |
| 3(j) next_step | `tabs/tab_m3.py` after the breakthrough panel (~line 1030) | Triggered when `lifecycle_result is not None`. |
| **OutputType extensions** | `core/decision_grade.py` after the existing PRESSURE_HEADROOM entry | Adds three enum members + three policy rows (mirrors v0.7 W-030 pattern). |

---

## §5 Cross-cutting design concerns

### 5.1 State management

| Session-state key | Owner | Consumers | Lifetime |
|---|---|---|---|
| `mobile_phase: MobilePhase` | 3(a) widget | 3(a, c, d, e), `tab_m3.py` pre-flight, lifecycle | Persists until user changes it |
| `isotherm_spec: IsothermSpec` | 3(b) widget | `tab_m3.py` breakthrough + gradient elution | Persists |
| `forward_mc_bands: Optional[MCEnvelopeBands]` | 3(c) | 3(j) (decides whether to highlight "next step") | Cleared on lifecycle re-run |
| `posterior_envelope: Optional[InferredPosteriorEnvelope]` | 3(d) | None (display only) | Cleared on lifecycle re-run |
| `posterior_log_cov: Optional[np.ndarray]` | 3(d) round-trip button | 3(c) ForwardMCRunInputs.log_cov | Persists across sessions until cleared |
| `multi_column_envelope: Optional[MultiColumnPressureEnvelope]` | 3(e) | 3(j) | Cleared on lifecycle re-run |
| `_cal_store: CalibrationStore` | 3(f) (existing) | Lifecycle, every panel | Persists |
| `_jump_to_calibration_section: Optional[str]` | 3(j) | tab_calibration dispatcher | One-shot read+clear |

### 5.2 DESIGN.md compliance

- No new colours introduced. The tier banner reuses existing semantic colours (green/amber/red) defined in DESIGN.md.
- The RecoveryAction timeline reuses the existing `_STATE_COLORS` palette in `tab_m3_monitor.py`.
- The forward-MC `p_blocker` chip uses the same green/amber/red ladder as the pre-flight headroom chip — visual vocabulary parity.

### 5.3 Tier-policy plumbing

**Three new `OutputType` enum members** to add to `core/decision_grade.py`:

| Member | Policy floor | Use case |
|---|---|---|
| `MC_PROBABILITY` | `SEMI_QUANTITATIVE` (mirrors PRESSURE_HEADROOM) | `p_blocker`, `p_warning` chips |
| `POSTERIOR_PARAMETER` | `SEMI_QUANTITATIVE` (per ADR-010 §"Tier mapping") | K_geom / μ / G_DN posterior quantiles |
| `ESS` | `QUALITATIVE_TREND` floor (always renders as NUMBER — it's a diagnostic, not a prediction) | Effective sample size from inverse inference |

All new metrics route through `render_metric`. All new chart annotations route through `render_decision_grade_annotation`. **No parallel mechanisms.**

### 5.4 v9.0 Family-First contract enforcement

- 3(b) isotherm selector dispatches on `polymer_family.value` and `binding_model_hint` — both consumed via `.value` comparisons, never `is`.
- 3(e) multi-column builder stores `polymer_family.value` per row.
- New OutputType members compared by `.value` per the existing decision_grade convention.

### 5.5 AST gate — `is`/`is not` comparison risks

| Site | Risk | Mitigation |
|---|---|---|
| 3(b) isotherm dropdown branching | `if choice is IsothermChoice.LANGMUIR:` would silently break after Streamlit rerun | Branch on `choice.value == IsothermChoice.LANGMUIR.value`; document in module docstring |
| 3(c) prior mode radio | Same risk on the radio's chosen value | Same mitigation |
| 3(g) timeline | RecoveryAction comparisons | Same mitigation |

The existing `tests/test_v9_3_enum_comparison_enforcement.py` AST scanner already covers `PolymerFamily`, `ACSSiteType`, `ModelEvidenceTier`, `ModelMode`. **Extend the scanner to also cover `IsothermChoice` and `OutputType`** — both are managed enums.

---

## §6 Forward audit — six-dimension predicted post-implementation verdict

| # | Dimension | Pre | Post | Remaining gap (v0.9) |
|---|---|---|---|---|
| D1 | Correctness | PASS | PASS | — |
| D2 | Completeness | FAIL | **PASS** | UNICORN socket UI (ADR-008 deferral); cyclic SMB UI (ADR-009 deferral); MCMC inverse UI (ADR-010 promotion target). All three are awaiting backend; not closeable in v0.8.4. |
| D3 | Modularity | PARTIAL | **PASS** | — |
| D4 | Scalability | PASS | PASS | — |
| D5 | Maintainability | PARTIAL | **PASS** | — |
| D6 | Scientific provenance | FAIL | **PASS** | Tier promotion to VALIDATED_QUANTITATIVE still requires the wet-lab holdout step that lives outside the UI. |

Aggregate post: **all six dimensions PASS**. Outstanding gaps are the three v0.9 hardware/backend deferrals only.

---

## §7 Dependency bundles for /dev-orchestrator

| Bundle | Components | Internal dependencies | External dependencies | Independent? |
|---|---|---|---|---|
| **A — foundation** | 3(a) mobile_phase + the 3(a) wire-ins at `tab_m3.py:320` and `lifecycle/orchestrator.py:781` | self-contained | requires the OutputType extensions in §5.3 | YES — ships first |
| **B — isotherm + plot tier** | 3(b) isotherm selector + 3(h) plots_m2 tier wire | 3(b) requires 3(a) only for the `mobile_phase` arg in some isotherm sub-forms | OutputType extensions optional | YES — can ship parallel to A |
| **C — uncertainty stack** | 3(c) forward MC + 3(d) inverse + the round-trip plumbing | 3(d) writes log_cov; 3(c) reads it | requires A (mobile_phase) + B (isotherm); requires `OutputType.MC_PROBABILITY`, `POSTERIOR_PARAMETER`, `ESS` | NO — must ship after A+B |
| **D — geometry** | 3(e) multi-column builder | self-contained except for A | requires A | YES — can ship parallel to C |
| **E — calibration** | 3(f) wetlab ingestion + 3(i) tier banner + the scanner extension for `IsothermChoice`/`OutputType` | banner reads tier from lifecycle result; ingestion reads/writes `_cal_store` | independent | YES — can ship parallel to A/B |
| **F — UX polish** | 3(g) RecoveryAction timeline + 3(j) next-step affordance | self-contained | requires A+B+C+D for "next-step" buttons to actually have destinations | NO — must ship last |

**Recommended sequencing for /dev-orchestrator:** A → (B parallel E) → C → (D parallel) → F. Six logical bundles map to ~6 work-item batches in the v0.8.4 plan.

---

## Phase-2 hand-off note to /dev-orchestrator (Phase 3)

The §3 contracts are implementation-ready. /dev-orchestrator should:
1. Assign W-numbers continuing from W-050 (last v0.8.3 item) — likely W-051 through W-062 across the bundles.
2. Assign batch IDs (B-1p, B-1q, B-2s, B-2t, B-2u, B-2v…) following the existing convention.
3. Choose model tiers per batch (Sonnet for most; the isotherm selector and inverse-inference panels are the most complex and may warrant Opus-tier review).
4. Define acceptance criteria per W-item from the §3 contracts and §4 seam map.
5. Pin a release tag (v0.8.4 per the patch-versioning policy; v0.9 still reserved for matured-status).

The spec is dense enough that /dev-orchestrator should not need to revisit /architect for clarification.

---

> **Disclaimer**: This architectural design is provided for informational and development purposes only. Computational architectures for safety-critical, medical, financial, or regulatory systems must be reviewed by qualified domain engineers before deployment. The author is an AI assistant; all designs should be validated through appropriate testing and peer review before production use.
