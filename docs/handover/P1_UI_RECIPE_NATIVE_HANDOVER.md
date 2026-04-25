# P1 UI Recipe-Native Handover

Date: 2026-04-25

## Purpose

This pass moves the Streamlit M1/M2/M3 control boundary onto `ProcessRecipe`.
The UI still uses the existing widgets and inherited numerical kernels, but the
session-level lifecycle source of truth is now a serialized recipe produced and
consumed through `dpsim.core.recipe_io`.

## Main Changes

- Added `dpsim.visualization.ui_recipe`.
  - Initializes `st.session_state["process_recipe"]` from
    `default_affinity_media_recipe()`.
  - Persists the recipe as plain serialized data via
    `process_recipe_to_dict()` / `process_recipe_from_dict()`.
  - Provides pure sync helpers for M1, M2, and M3 Streamlit controls.

- Updated Streamlit app initialization.
  - `visualization/app.py` now ensures recipe state exists before tab rendering.

- Updated M1.
  - M1 controls write rpm, emulsification time, oil temperature, surfactant,
    cooling rate, volumes, hardware mode, polymer family, and target product
    values into `ProcessRecipe`.
  - M1 runs now call `resolve_lifecycle_inputs(recipe, base_params=params)`
    before `PipelineOrchestrator.run_single()`, so recipe-owned M1 quantities
    overwrite the legacy `SimulationParameters` fields.

- Updated M2.
  - M2 UI `ModificationStep` controls are converted into recipe M2
    `ProcessStep` operations.
  - M2 execution resolves backend `ModificationStep` objects from the recipe
    instead of running the raw widget list directly.
  - Added recipe support for `ProcessStepKind.PROTEIN_PRETREATMENT`.

- Updated M3.
  - M3 column geometry, load feed, flow rate, durations, buffer pH/conductivity,
    elution settings, and gradient metadata write into recipe M3 method steps.
  - M3 breakthrough and Protein A method execution consume resolved recipe
    column/method/feed/flow values.

## Scientific Notes

- The UI recipe sync layer is intentionally an adapter, not a solver. It should
  not duplicate validation or kinetics logic already owned by
  `dpsim.lifecycle.recipe_resolver` and downstream module kernels.
- M1 still requires `base_params` because several family-specific formulation
  and solver fields are not yet represented in `ProcessRecipe`.
- M3 salt-gradient controls are stored in recipe metadata, while the current
  gradient solver still consumes its existing gradient object directly.

## Verification

- Focused recipe/resolver tests:
  - `tests/test_ui_recipe.py`
  - `tests/lifecycle/test_p1_scientific_boundaries.py`
  - `tests/core/test_process_recipe_io.py`

- Broader UI/lifecycle subset:
  - `tests/test_ui_contract.py`
  - `tests/core/test_clean_architecture.py`
  - `tests/lifecycle/test_p3_m2_functionalization.py`
  - `tests/lifecycle/test_p4_m3_method.py`

- Full regression:
  - `1089 passed, 2 xfailed, 40 warnings`

## Remaining P1 Work

- Move CLI M1 default construction away from
  `recipe_from_simulation_parameters()` once CLI argument parsing can emit
  `ProcessRecipe` directly.
- Decide whether family-specific M1 formulation fields should become formal
  recipe material properties or remain solver-only `base_params`.
- Add optional UI import/export buttons for recipe JSON/TOML after the state
  contract stabilizes.
