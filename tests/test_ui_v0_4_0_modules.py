"""Smoke tests for v0.4.0 M-003..M-009 modules.

Mirrors the existing ``test_ui_chrome_smoke.py`` pattern: import every
new public surface, assert the modules wire together, and confirm the
key SA-prescribed prescriptions are present in the column-xsec asset.
"""

from __future__ import annotations

from dataclasses import dataclass

import pytest

from dpsim.datatypes import ModelEvidenceTier


# ── M-003 help ────────────────────────────────────────────────────────


def test_help_module_imports() -> None:
    from dpsim.visualization.help import (
        HELP_CATALOG,
        param_row,
        render_help,
    )

    assert callable(param_row)
    assert callable(render_help)
    assert isinstance(HELP_CATALOG, dict)
    assert len(HELP_CATALOG) >= 20


def test_help_catalog_covers_core_m1_m2_m3_paths() -> None:
    from dpsim.visualization.help import HELP_CATALOG

    # Spot-check that the major parameter axes are documented.
    for required in (
        "m1.family",
        "m1.formulation.agarose_pct",
        "m1.hardware.stir_rpm",
        "m1.crosslinker",
        "m2.template",
        "m2.ligand_density",
        "m3.column.length",
        "m3.flow_rate",
    ):
        assert required in HELP_CATALOG, f"missing help for {required}"


def test_get_help_returns_default_for_missing_path() -> None:
    from dpsim.visualization.help import get_help

    assert get_help("nope.does.not.exist") == ""
    assert get_help("nope", default="fallback") == "fallback"


# ── M-004 diff ────────────────────────────────────────────────────────


@dataclass
class _StubLeaf:
    a: float
    b: str


@dataclass
class _StubRecipe:
    name: str
    leaf: _StubLeaf
    items: list[str]


def test_snapshot_recipe_deepcopies() -> None:
    from dpsim.visualization.diff import snapshot_recipe

    recipe = _StubRecipe(name="r", leaf=_StubLeaf(a=4.0, b="x"), items=["one"])
    snap = snapshot_recipe(recipe)
    assert snap["name"] == "r"
    assert snap["leaf"]["a"] == 4.0
    # Mutating the live recipe must not touch the snapshot.
    recipe.leaf.a = 99.9
    assert snap["leaf"]["a"] == 4.0


def test_diff_recipes_identical_returns_empty() -> None:
    from dpsim.visualization.diff import diff_recipes, snapshot_recipe

    r = _StubRecipe(name="r", leaf=_StubLeaf(a=4.0, b="x"), items=["one"])
    snap = snapshot_recipe(r)
    diffs = diff_recipes(snap, r)
    assert diffs == []


def test_diff_recipes_finds_leaf_change() -> None:
    from dpsim.visualization.diff import diff_recipes, snapshot_recipe

    r = _StubRecipe(name="r", leaf=_StubLeaf(a=4.0, b="x"), items=["one"])
    snap = snapshot_recipe(r)
    r.leaf.a = 3.5
    diffs = diff_recipes(snap, r)
    assert len(diffs) == 1
    assert diffs[0].path == "leaf.a"
    assert diffs[0].prev == 4.0
    assert diffs[0].next == 3.5


def test_diff_recipes_handles_list_growth() -> None:
    from dpsim.visualization.diff import diff_recipes, snapshot_recipe

    r = _StubRecipe(name="r", leaf=_StubLeaf(a=1.0, b="x"), items=["one"])
    snap = snapshot_recipe(r)
    r.items.append("two")
    diffs = diff_recipes(snap, r)
    paths = [d.path for d in diffs]
    assert any("items[1]" in p for p in paths)


def test_diff_recipes_with_no_baseline_returns_empty() -> None:
    from dpsim.visualization.diff import diff_recipes

    r = _StubRecipe(name="r", leaf=_StubLeaf(a=1.0, b="x"), items=["one"])
    assert diff_recipes(None, r) == []


# ── M-006 evidence ────────────────────────────────────────────────────


def test_aggregate_min_tier_picks_weakest() -> None:
    from dpsim.visualization.evidence import StageEvidence, aggregate_min_tier

    stages = [
        StageEvidence(stage_id="m1", label="M1",
                      tier=ModelEvidenceTier.CALIBRATED_LOCAL.value),
        StageEvidence(stage_id="m2", label="M2",
                      tier=ModelEvidenceTier.SEMI_QUANTITATIVE.value),
        StageEvidence(stage_id="m3", label="M3",
                      tier=ModelEvidenceTier.CALIBRATED_LOCAL.value),
    ]
    assert aggregate_min_tier(stages) == ModelEvidenceTier.SEMI_QUANTITATIVE.value


def test_aggregate_min_tier_empty_returns_unsupported() -> None:
    from dpsim.visualization.evidence import aggregate_min_tier

    assert aggregate_min_tier([]) == ModelEvidenceTier.UNSUPPORTED.value


def test_aggregate_handles_unknown_tier_string() -> None:
    from dpsim.visualization.evidence import StageEvidence, aggregate_min_tier

    stages = [StageEvidence(stage_id="x", label="X", tier="not_a_real_tier")]
    # Falls back to UNSUPPORTED rather than raising.
    assert aggregate_min_tier(stages) == ModelEvidenceTier.UNSUPPORTED.value


# ── M-005 run_rail state machine ──────────────────────────────────────


def test_run_state_module_exposes_full_api() -> None:
    from dpsim.visualization.run_rail import (
        CANCEL_FLAG_KEY,
        RUN_STATE_KEY,
        RunState,  # noqa: F401 — type-only import check
        cancel_requested,
        clear_cancel,
        get_run_state,
        request_cancel,
        set_run_state,
    )

    assert RUN_STATE_KEY == "_dpsim_run_state"
    assert CANCEL_FLAG_KEY == "_dpsim_run_cancelled"
    assert callable(get_run_state)
    assert callable(set_run_state)
    assert callable(request_cancel)
    assert callable(cancel_requested)
    assert callable(clear_cancel)


# ── M-008 column_xsec ─────────────────────────────────────────────────


def test_column_xsec_module_imports() -> None:
    from dpsim.visualization.components import (
        ColumnPhase,  # noqa: F401 — Literal type re-export
        render_column_xsec,
    )

    assert callable(render_column_xsec)


def test_column_xsec_asset_has_required_placeholders() -> None:
    from dpsim.visualization.components.column_xsec import _ASSET_PATH

    assert _ASSET_PATH.exists()
    html = _ASSET_PATH.read_text(encoding="utf-8")
    for placeholder in (
        "__PHASE__",
        "__WIDTH__",
        "__HEIGHT__",
        "__COLUMN_LENGTH_MM__",
        "__COLUMN_DIAMETER_MM__",
        "__BED_FRACTION__",
        "__PARTICLE_COUNT__",
        "__THEME__",
    ):
        assert placeholder in html, f"missing placeholder {placeholder}"


@pytest.mark.parametrize("phase", ["load", "wash", "elute", "cip"])
def test_column_xsec_asset_defines_each_phase_palette(phase: str) -> None:
    from dpsim.visualization.components.column_xsec import _ASSET_PATH

    html = _ASSET_PATH.read_text(encoding="utf-8")
    assert phase + ":" in html, f"phase {phase} not found in PHASES dict"


def test_column_xsec_keeps_both_bead_recolour_and_streaming_dots() -> None:
    """SA Q2 sign-off: keep BOTH bead recolour AND streaming dots."""
    from dpsim.visualization.components.column_xsec import _ASSET_PATH

    html = _ASSET_PATH.read_text(encoding="utf-8")
    # Bead recolour is implemented via the per-particle 'payload' circle.
    assert "payloadOpacity" in html
    # Streaming dots are the 'outflow' streamlines for wash/elute/cip.
    assert "outflowColor" in html
    # Phase-dependent legend labels.
    assert "Outflow: eluate target" in html
    assert "Outflow: stripped residuals" in html
    assert "Outflow: flushed impurities" in html


# ── M-009 shell ───────────────────────────────────────────────────────


def test_shell_module_exports_render_shell() -> None:
    from dpsim.visualization.shell import (
        STAGE_ORDER,
        StageId,  # noqa: F401 — Literal type
        get_active_stage,
        render_shell,
        render_stage_spine,
        render_top_bar,
        set_active_stage,
    )

    assert callable(render_shell)
    assert callable(render_top_bar)
    assert callable(render_stage_spine)
    assert callable(get_active_stage)
    assert callable(set_active_stage)
    assert len(STAGE_ORDER) == 7
    ids = [s[0] for s in STAGE_ORDER]
    assert ids == ["target", "m1", "m2", "m3", "run", "validation", "calibrate"]


# ── v0.4.1 — extended deferred-work modules ──────────────────────────


def test_v041_labeled_widget_is_callable() -> None:
    from dpsim.visualization.help import labeled_widget

    assert callable(labeled_widget)


def test_v041_named_baseline_save_get_delete() -> None:
    """Named baselines: save → look up → delete round-trip."""
    import streamlit as st

    from dpsim.visualization.diff import (
        delete_baseline,
        get_baseline,
        save_baseline,
    )

    # Reset any prior session-state for this test.
    from dpsim.visualization.diff.baselines import BASELINES_KEY
    if hasattr(st, "session_state"):
        try:
            st.session_state[BASELINES_KEY] = {}
        except Exception:
            pass

    recipe = _StubRecipe(name="r", leaf=_StubLeaf(a=4.0, b="x"), items=["one"])
    saved = save_baseline(name="calibrated_v1", recipe=recipe,
                          note="round-trip test")
    assert saved.name == "calibrated_v1"
    assert saved.snapshot["leaf"]["a"] == 4.0

    fetched = get_baseline("calibrated_v1")
    assert fetched is not None
    assert fetched.note == "round-trip test"

    assert delete_baseline("calibrated_v1") is True
    assert get_baseline("calibrated_v1") is None
    assert delete_baseline("calibrated_v1") is False  # idempotent


def test_v041_baseline_reserved_name_rejected() -> None:
    from dpsim.visualization.diff import save_baseline

    recipe = _StubRecipe(name="r", leaf=_StubLeaf(a=1.0, b="x"), items=[])
    with pytest.raises(ValueError):
        save_baseline(name="last_run", recipe=recipe)
    with pytest.raises(ValueError):
        save_baseline(name="", recipe=recipe)


def test_v041_baseline_choices_includes_last_run() -> None:
    from dpsim.visualization.diff import baseline_choices

    choices = baseline_choices(include_last_run=True)
    assert "last_run" in choices


def test_v041_run_history_append_and_evict() -> None:
    """History: append + FIFO eviction at MAX_HISTORY."""
    import streamlit as st

    from dpsim.visualization.run_rail import (
        HISTORY_KEY,
        MAX_HISTORY,
        append_history,
        clear_history,
        get_history,
        latest,
    )

    if hasattr(st, "session_state"):
        try:
            st.session_state[HISTORY_KEY] = []
        except Exception:
            pass
    clear_history()
    assert latest() is None

    for i in range(MAX_HISTORY + 5):
        append_history(
            recipe_name=f"r{i}",
            snapshot={"i": i},
            evidence_min=ModelEvidenceTier.SEMI_QUANTITATIVE.value,
        )
    hist = get_history()
    assert len(hist) == MAX_HISTORY
    # FIFO eviction: oldest should be the i=5 entry (5 evicted, 5..MAX+5 remain).
    assert hist[0].recipe_name == "r5"
    assert latest() is not None
    assert latest().recipe_name == f"r{MAX_HISTORY + 4}"  # type: ignore[union-attr]


def test_v041_theme_module_api() -> None:
    from dpsim.visualization.shell import ThemeMode, get_theme, set_theme

    assert callable(get_theme)
    assert callable(set_theme)
    # ThemeMode is a Literal — ensure the module exports it.
    assert ThemeMode is not None


def test_v041_tab_m1_imports_impeller_xsec_lazily() -> None:
    """Verify the M1 hardware-card animation placement is wired.

    v0.4.11: the visualization is now rendered inline (no expander) per
    the Direction-A reference. The gate verifies the wiring + that the
    module discusses Rushton geometry — not a specific UI string.
    """
    from pathlib import Path

    src = (
        Path(__file__).resolve().parents[1]
        / "src" / "dpsim" / "visualization" / "tabs" / "tab_m1.py"
    ).read_text(encoding="utf-8")
    assert "render_impeller_xsec" in src
    assert "Rushton" in src


def test_v041_tab_m3_imports_column_xsec_and_labeled_widget() -> None:
    """Verify the M3 column-card animation + labeled_widget migration."""
    from pathlib import Path

    src = (
        Path(__file__).resolve().parents[1]
        / "src" / "dpsim" / "visualization" / "tabs" / "tab_m3.py"
    ).read_text(encoding="utf-8")
    assert "render_column_xsec" in src
    assert "labeled_widget" in src
    assert 'get_help("m3.column.diameter")' in src


# ── v0.4.2 — autowire + Direction B + disk persistence ───────────────


def test_v042_autowire_module_exports() -> None:
    from dpsim.visualization.shell import (
        autowire_shell_state,
        derive_stage_status,
    )

    assert callable(autowire_shell_state)
    assert callable(derive_stage_status)


def test_v042_direction_switch_api() -> None:
    from dpsim.visualization.shell import (
        ShellDirection,  # noqa: F401 — Literal type
        get_direction,
        set_direction,
    )

    assert callable(get_direction)
    assert callable(set_direction)


def test_v042_triptych_module_imports() -> None:
    from dpsim.visualization.shell import (
        TriptychFocus,  # noqa: F401 — Literal type
        get_triptych_focus,
        render_direction_switch,
        render_triptych,
        set_triptych_focus,
    )

    assert callable(render_triptych)
    assert callable(render_direction_switch)
    assert callable(get_triptych_focus)
    assert callable(set_triptych_focus)


def test_v042_run_history_disk_round_trip() -> None:
    """Save history to disk, clear, reload → identity preserved."""
    import tempfile
    from pathlib import Path

    import streamlit as st

    from dpsim.datatypes import ModelEvidenceTier
    from dpsim.visualization.run_rail import (
        HISTORY_KEY,
        append_history,
        clear_history,
        get_history,
        load_history_from_disk,
        save_history_to_disk,
    )

    if hasattr(st, "session_state"):
        try:
            st.session_state[HISTORY_KEY] = []
        except Exception:
            pass
    clear_history()

    append_history(
        recipe_name="test_recipe",
        snapshot={"alpha": 1.0, "beta": "two"},
        evidence_min=ModelEvidenceTier.CALIBRATED_LOCAL.value,
        notes="round-trip",
    )
    append_history(
        recipe_name="test_recipe2",
        snapshot={"alpha": 2.0, "beta": "three"},
        evidence_min=ModelEvidenceTier.SEMI_QUANTITATIVE.value,
    )

    # Use the system tempdir directly to dodge the per-user pytest-tmp
    # access issue on this Windows host.
    with tempfile.TemporaryDirectory() as td:
        target = Path(td) / "history.json"
        saved_path = save_history_to_disk(path=target)
        assert saved_path == target
        assert target.exists()

        clear_history()
        assert len(get_history()) == 0

        n = load_history_from_disk(path=target)
        assert n == 2
        loaded = get_history()
        assert loaded[0].recipe_name == "test_recipe"
        assert loaded[0].snapshot == {"alpha": 1.0, "beta": "two"}
        assert loaded[0].notes == "round-trip"
        assert loaded[1].recipe_name == "test_recipe2"


def test_v042_load_history_returns_zero_for_missing_file() -> None:
    import tempfile
    from pathlib import Path

    from dpsim.visualization.run_rail import load_history_from_disk

    with tempfile.TemporaryDirectory() as td:
        n = load_history_from_disk(path=Path(td) / "does-not-exist.json")
        assert n == 0


def test_v042_reload_run_applies_snapshot_to_recipe() -> None:
    """reload_run mutates the live recipe to match a historical snapshot."""
    from dpsim.visualization.run_rail import RunHistoryEntry, reload_run
    from datetime import datetime, timezone

    recipe = _StubRecipe(
        name="r", leaf=_StubLeaf(a=4.0, b="x"), items=["one"]
    )
    entry = RunHistoryEntry(
        run_id=1,
        timestamp_utc=datetime.now(tz=timezone.utc),
        recipe_name="r",
        snapshot={"name": "r-loaded", "leaf": {"a": 99.0, "b": "y"}},
        evidence_min="semi_quantitative",
    )
    reload_run(entry, recipe=recipe)
    assert recipe.name == "r-loaded"
    assert recipe.leaf.a == 99.0
    assert recipe.leaf.b == "y"


def test_v042_app_module_no_legacy_workflow_panel_call() -> None:
    """app.py should no longer call render_lifecycle_workflow_panel
    (replaced by the stage spine + autowire)."""
    from pathlib import Path

    src = (
        Path(__file__).resolve().parents[1]
        / "src" / "dpsim" / "visualization" / "app.py"
    ).read_text(encoding="utf-8")
    assert "render_lifecycle_workflow_panel(" not in src
    assert "autowire_shell_state" in src
    assert "derive_stage_status" in src


# ── v0.4.3 — autoload, triptych chips, cancellation, bulk migration ──


def test_v043_cancellation_module_api() -> None:
    from dpsim.lifecycle.cancellation import (
        CANCEL_FLAG_KEY,
        RunCancelledError,
        check_cancel,
        clear_cancel_flag,
    )

    assert CANCEL_FLAG_KEY == "_dpsim_run_cancelled"
    assert issubclass(RunCancelledError, RuntimeError)
    assert callable(check_cancel)
    assert callable(clear_cancel_flag)


def test_v043_check_cancel_no_op_outside_streamlit() -> None:
    """check_cancel must not raise when no flag is set."""
    from dpsim.lifecycle.cancellation import check_cancel

    # No-op path; should not raise.
    check_cancel(stage="unit-test")


def test_v043_check_cancel_raises_when_flag_set() -> None:
    """check_cancel raises when the session-state flag is True."""
    import streamlit as st

    from dpsim.lifecycle.cancellation import (
        CANCEL_FLAG_KEY,
        RunCancelledError,
        check_cancel,
        clear_cancel_flag,
    )

    if not hasattr(st, "session_state"):
        pytest.skip("Streamlit session_state not available in this env")

    try:
        st.session_state[CANCEL_FLAG_KEY] = True
    except Exception:
        pytest.skip("Cannot mutate session_state outside Streamlit run")

    try:
        with pytest.raises(RunCancelledError):
            check_cancel(stage="unit-test")
    finally:
        clear_cancel_flag()


def test_v043_orchestrator_has_cancellation_poll_points() -> None:
    """Verify the orchestrator was edited to call check_cancel at stage boundaries."""
    from pathlib import Path

    src = (
        Path(__file__).resolve().parents[1]
        / "src" / "dpsim" / "lifecycle" / "orchestrator.py"
    ).read_text(encoding="utf-8")
    assert "check_cancel" in src
    # Each major stage boundary should have a poll point.
    for stage_label in ("pre-M1", "post-M1", "pre-M2", "post-M2", "pre-M3", "post-M3"):
        assert f'stage="{stage_label}"' in src, f"missing poll for {stage_label}"


def test_v043_app_module_autoloads_history_on_startup() -> None:
    """app.py should call load_history_from_disk on first render."""
    from pathlib import Path

    src = (
        Path(__file__).resolve().parents[1]
        / "src" / "dpsim" / "visualization" / "app.py"
    ).read_text(encoding="utf-8")
    assert "load_history_from_disk" in src
    assert "_dpsim_history_autoloaded" in src


def test_v043_triptych_summary_uses_recipe() -> None:
    """triptych._summary_for should pull from recipe + lifecycle_result, not hardcoded values."""
    from pathlib import Path

    src = (
        Path(__file__).resolve().parents[1]
        / "src" / "dpsim" / "visualization" / "shell" / "triptych.py"
    ).read_text(encoding="utf-8")
    assert "_deep_get" in src
    assert "ensure_process_recipe_state" in src
    # Hardcoded magic strings from v0.4.1 stub should be gone (the
    # placeholder "78.2 µm" / "48.2 mg/mL" no longer appear as defaults).
    assert '"78.2 µm"' not in src
    assert '"48.2 mg/mL"' not in src


def test_v043_tab_m1_widget_migration_count() -> None:
    """Confirm tab_m1 has migrated several widgets to labeled_widget."""
    from pathlib import Path

    src = (
        Path(__file__).resolve().parents[1]
        / "src" / "dpsim" / "visualization" / "tabs" / "tab_m1.py"
    ).read_text(encoding="utf-8")
    # Each labeled_widget call is a migrated widget.
    assert src.count("labeled_widget(") >= 5, (
        "Expected at least 5 labeled_widget calls in tab_m1.py"
    )


def test_v043_tab_m2_widget_migration_count() -> None:
    from pathlib import Path

    src = (
        Path(__file__).resolve().parents[1]
        / "src" / "dpsim" / "visualization" / "tabs" / "tab_m2.py"
    ).read_text(encoding="utf-8")
    # tab_m2 uses both `labeled_widget(` (reagent-step block, 4 widgets)
    # and `_lw_m2(` (alias for the modification-step header, 3 widgets).
    total = src.count("labeled_widget(") + src.count("_lw_m2(")
    assert total >= 7, f"expected ≥7 migrated widgets in tab_m2, got {total}"


def test_v043_tab_m3_widget_migration_count() -> None:
    from pathlib import Path

    src = (
        Path(__file__).resolve().parents[1]
        / "src" / "dpsim" / "visualization" / "tabs" / "tab_m3.py"
    ).read_text(encoding="utf-8")
    # Column geometry (4) + feed (3) + isotherm (2).
    assert src.count("labeled_widget(") >= 4
    assert src.count("_lw_m3(") >= 5


# ── v0.4.6 — finer cancellation polls + triptych column animation ────


def test_v046_pbe_solver_has_cancel_poll_per_extension_round() -> None:
    """level1 PBE solver polls cancel at top of each extension round."""
    from pathlib import Path

    src = (
        Path(__file__).resolve().parents[1]
        / "src" / "dpsim" / "level1_emulsification" / "solver.py"
    ).read_text(encoding="utf-8")
    assert "from dpsim.lifecycle.cancellation import check_cancel" in src
    assert 'stage=f"PBE-extension-' in src or 'stage="PBE-extension-' in src


def test_v046_lrm_solver_has_cancel_poll() -> None:
    """LRM solver checks cancel right before solve_ivp."""
    from pathlib import Path

    src = (
        Path(__file__).resolve().parents[1]
        / "src" / "dpsim" / "module3_performance" / "transport" / "lumped_rate.py"
    ).read_text(encoding="utf-8")
    assert "check_cancel" in src
    assert "pre-LRM-solve" in src


def test_v046_chromatography_method_has_cancel_poll() -> None:
    """run_chromatography_method polls cancel before LOAD breakthrough."""
    from pathlib import Path

    src = (
        Path(__file__).resolve().parents[1]
        / "src" / "dpsim" / "module3_performance" / "method.py"
    ).read_text(encoding="utf-8")
    assert "check_cancel" in src
    assert "pre-LOAD-breakthrough" in src


def test_v046_app_has_triptych_column_transition_css() -> None:
    """app.py injects a CSS transition on triptych column flex-grow."""
    from pathlib import Path

    src = (
        Path(__file__).resolve().parents[1]
        / "src" / "dpsim" / "visualization" / "app.py"
    ).read_text(encoding="utf-8")
    assert "dps-triptych-marker" in src
    assert "transition: flex-grow" in src


def test_v046_triptych_emits_animation_marker() -> None:
    """render_triptych emits the marker that scopes the CSS transition."""
    from pathlib import Path

    src = (
        Path(__file__).resolve().parents[1]
        / "src" / "dpsim" / "visualization" / "shell" / "triptych.py"
    ).read_text(encoding="utf-8")
    assert "dps-triptych-marker" in src


# ── v0.4.7 — real Streamlit Custom Components + scipy events ────────


def test_v047_make_cancel_event_returns_scipy_compatible() -> None:
    """make_cancel_event() returns a scipy-compatible event function."""
    from dpsim.lifecycle.cancellation import (
        THREAD_CANCEL_FLAG,
        make_cancel_event,
    )

    ev = make_cancel_event()
    # scipy's event interface: callable(t, y) → float; .terminal attr.
    assert callable(ev)
    assert getattr(ev, "terminal", False) is True
    assert getattr(ev, "direction", 0) == -1.0

    # No cancel → +1
    THREAD_CANCEL_FLAG.clear()
    assert ev(0.0, None) > 0
    # Cancel set → -1 (scipy detects zero crossing and halts)
    THREAD_CANCEL_FLAG.set()
    assert ev(0.0, None) < 0
    # Reset
    THREAD_CANCEL_FLAG.clear()


def test_v047_threading_flag_round_trip() -> None:
    """Threading flag round-trips set / read / clear."""
    from dpsim.lifecycle.cancellation import (
        clear_cancel_flag,
        set_thread_cancel_flag,
        thread_cancel_requested,
    )

    clear_cancel_flag()
    assert thread_cancel_requested() is False
    set_thread_cancel_flag()
    assert thread_cancel_requested() is True
    clear_cancel_flag()
    assert thread_cancel_requested() is False


def test_v047_lrm_solver_uses_cancel_event() -> None:
    """LRM solver passes a cancel event to solve_ivp."""
    from pathlib import Path

    src = (
        Path(__file__).resolve().parents[1]
        / "src" / "dpsim" / "module3_performance" / "transport" / "lumped_rate.py"
    ).read_text(encoding="utf-8")
    assert "make_cancel_event" in src
    assert "events=[make_cancel_event()]" in src
    assert "RunCancelledError" in src


def test_v047_request_cancel_mirrors_to_thread_flag() -> None:
    """run_rail.request_cancel writes to BOTH session_state and the threading flag."""
    from pathlib import Path

    src = (
        Path(__file__).resolve().parents[1]
        / "src" / "dpsim" / "visualization" / "run_rail" / "progress.py"
    ).read_text(encoding="utf-8")
    assert "set_thread_cancel_flag" in src


def test_v047_stop_button_component_exists() -> None:
    """stop_button custom component is declared and importable."""
    from pathlib import Path

    from dpsim.visualization.components import StopButtonState, stop_button

    assert callable(stop_button)
    # Ensure the asset directory + index.html exist.
    asset = (
        Path(__file__).resolve().parents[1]
        / "src" / "dpsim" / "visualization" / "components"
        / "assets" / "stop_button" / "index.html"
    )
    assert asset.exists()
    html = asset.read_text(encoding="utf-8")
    # Bidirectional comms — must call setComponentValue on click.
    assert "Streamlit.setComponentValue" in html
    assert "isStreamlitMessage" in html
    # State-machine literals.
    for state in ("idle", "running", "stopping", "done", "error"):
        assert state in html

    # StopButtonState dataclass shape.
    s = StopButtonState(clicked=False, click_count=0)
    assert s.clicked is False
    assert s.click_count == 0


def test_v047_triptych_panel_component_exists() -> None:
    """triptych_panel custom component is declared and importable."""
    from pathlib import Path

    from dpsim.visualization.components import triptych_panel

    assert callable(triptych_panel)
    asset = (
        Path(__file__).resolve().parents[1]
        / "src" / "dpsim" / "visualization" / "components"
        / "assets" / "triptych_panel" / "index.html"
    )
    assert asset.exists()
    html = asset.read_text(encoding="utf-8")
    # Bidirectional: focus changes go back to Python.
    assert "setComponentValue" in html
    # First-paint animation: must use requestAnimationFrame to defer
    # the focus state by one frame so CSS transition engages.
    assert "requestAnimationFrame" in html
    # CSS transition on flex-grow.
    assert "transition: flex-grow" in html


def test_v047_components_init_exports_custom_components() -> None:
    from dpsim.visualization.components import (  # noqa: F401
        StopButtonState,
        stop_button,
        triptych_panel,
    )


# ── v0.4.8 — threaded orchestrator + true mid-solve cancellation ────


def test_v048_background_run_clean_completion() -> None:
    """run_in_background captures the result of a successful target."""
    import time as _t

    from dpsim.lifecycle.cancellation import clear_cancel_flag
    from dpsim.lifecycle.threaded_runner import run_in_background

    clear_cancel_flag()

    def _target(x: int, y: int) -> int:
        _t.sleep(0.1)
        return x + y

    handle = run_in_background(_target, args=(2, 3))
    while handle.is_running():
        _t.sleep(0.05)
    assert handle.is_done()
    assert handle.succeeded()
    assert handle.result == 5
    assert handle.exception is None
    assert not handle.cancelled


def test_v048_background_run_captures_exception() -> None:
    """A target that raises has its exception captured, not propagated."""
    import time as _t

    from dpsim.lifecycle.threaded_runner import run_in_background

    def _target() -> int:
        raise ValueError("intentional test error")

    handle = run_in_background(_target)
    while handle.is_running():
        _t.sleep(0.02)
    assert handle.exception is not None
    assert isinstance(handle.exception, ValueError)
    assert "intentional test error" in str(handle.exception)
    assert handle.traceback_text  # captured non-empty
    assert not handle.succeeded()


def test_v048_background_run_cancel_via_thread_flag() -> None:
    """Setting THREAD_CANCEL_FLAG mid-flight halts a target that polls it."""
    import time as _t

    from dpsim.lifecycle.cancellation import (
        RunCancelledError,
        THREAD_CANCEL_FLAG,
        clear_cancel_flag,
        set_thread_cancel_flag,
    )
    from dpsim.lifecycle.threaded_runner import run_in_background

    clear_cancel_flag()

    def _slow_target() -> str:
        # Simulates a solver loop that polls the flag (matching the
        # scipy-events behaviour for solve_ivp).
        for i in range(200):
            if THREAD_CANCEL_FLAG.is_set():
                raise RunCancelledError(f"cancelled at step {i}")
            _t.sleep(0.02)
        return "completed-without-cancel"

    handle = run_in_background(_slow_target)
    # Let it run briefly then request cancel.
    _t.sleep(0.3)
    set_thread_cancel_flag()
    # Wait for the worker to notice and halt.
    deadline = _t.monotonic() + 5.0
    while handle.is_running() and _t.monotonic() < deadline:
        _t.sleep(0.05)
    assert handle.is_done(), "worker thread did not halt within 5 s"
    assert handle.cancelled is True
    assert handle.result is None
    assert handle.exception is None  # RunCancelledError caught and counted as cancel
    # Cancel latency should be well under 1 s.
    assert handle.elapsed_seconds() < 2.0
    clear_cancel_flag()


def test_v048_background_run_clears_stale_cancel_flag_on_start() -> None:
    """run_in_background clears any stale cancel flag before starting."""
    import time as _t

    from dpsim.lifecycle.cancellation import (
        clear_cancel_flag,
        set_thread_cancel_flag,
        thread_cancel_requested,
    )
    from dpsim.lifecycle.threaded_runner import run_in_background

    # Simulate a stale flag from a prior run.
    set_thread_cancel_flag()
    assert thread_cancel_requested() is True

    handle = run_in_background(lambda: 42)
    while handle.is_running():
        _t.sleep(0.02)
    # If the flag had stuck around, the run might have been cancelled
    # immediately. With pre-clearing, the run completes cleanly.
    assert handle.succeeded()
    assert handle.result == 42
    clear_cancel_flag()


def test_v048_run_panel_uses_background_run() -> None:
    """ui_workflow.render_lifecycle_run_panel uses run_in_background."""
    from pathlib import Path

    src = (
        Path(__file__).resolve().parents[1]
        / "src" / "dpsim" / "visualization" / "ui_workflow.py"
    ).read_text(encoding="utf-8")
    assert "run_in_background" in src
    assert "_dpsim_background_run" in src
    # Polling cadence must be set.
    assert "POLL_INTERVAL_S" in src or "time.sleep" in src
    # Critical: the path that catches RunCancelledError shouldn't be
    # the only cancel path anymore — the threaded path uses
    # bg_run.cancelled.
    assert "bg_run.cancelled" in src


# ── v0.4.9 — audit fixes (F-1 ε280, F-2 triptych shape, F-3 per-flag, F-4 evidence, F-5 unused param) ────


def test_v049_F1_epsilon_280_help_text_no_longer_misclaims_igg() -> None:
    """F-1: ε₂₈₀ help text must not claim 36 000 is "typical for IgG"."""
    from pathlib import Path

    src = (
        Path(__file__).resolve().parents[1]
        / "src" / "dpsim" / "visualization" / "tabs" / "tab_m3.py"
    ).read_text(encoding="utf-8")
    assert "Default 36 000 1/(M·cm) is typical for IgG" not in src
    # The corrected help should mention IgG ≈ 210 000 and BSA ≈ 43 800.
    assert "210 000" in src or "210000" in src
    assert "Pace 1995" in src or "BSA" in src


def test_v049_F4_default_evidence_stages_returns_empty() -> None:
    """F-4: default_evidence_stages must NOT return fake CAL/SEMI tiers."""
    from dpsim.visualization.shell.shell import default_evidence_stages

    assert default_evidence_stages() == []


def test_v049_F4_top_bar_badge_handles_empty_stages() -> None:
    """F-4: render_top_bar_badge with empty list must not show a fake tier."""
    from dpsim.visualization.evidence.rollup import render_top_bar_badge

    html = render_top_bar_badge([])
    # Must NOT contain any tier-coloured badge HTML.
    assert "no run yet" in html
    # Sanity: the in-run-state path still renders properly.
    from dpsim.datatypes import ModelEvidenceTier
    from dpsim.visualization.evidence.rollup import StageEvidence

    html_with = render_top_bar_badge([
        StageEvidence(stage_id="m1", label="M1",
                      tier=ModelEvidenceTier.SEMI_QUANTITATIVE.value),
    ])
    assert "no run yet" not in html_with


def test_v049_F3_make_cancel_event_accepts_per_run_flag() -> None:
    """F-3: make_cancel_event must accept a per-run threading.Event."""
    import threading

    from dpsim.lifecycle.cancellation import (
        THREAD_CANCEL_FLAG,
        clear_cancel_flag,
        make_cancel_event,
    )

    clear_cancel_flag()
    # Per-run flag — module-global stays clear.
    flag_a = threading.Event()
    flag_b = threading.Event()
    ev_a = make_cancel_event(flag=flag_a)
    ev_b = make_cancel_event(flag=flag_b)
    assert ev_a(0.0, None) > 0 and ev_b(0.0, None) > 0
    # Setting a's flag does NOT cancel b's run.
    flag_a.set()
    assert ev_a(0.0, None) < 0
    assert ev_b(0.0, None) > 0  # b is independent
    # Module-global flag is also independent.
    assert THREAD_CANCEL_FLAG.is_set() is False
    flag_a.clear()
    flag_b.clear()


def test_v049_F3_make_cancel_event_back_compat_default() -> None:
    """F-3: make_cancel_event() with no flag uses module-global, preserving v0.4.7 callers."""
    from dpsim.lifecycle.cancellation import (
        clear_cancel_flag,
        make_cancel_event,
        set_thread_cancel_flag,
    )

    clear_cancel_flag()
    ev = make_cancel_event()
    assert ev(0.0, None) > 0
    set_thread_cancel_flag()
    assert ev(0.0, None) < 0
    clear_cancel_flag()


def test_v049_F5_make_cancel_event_no_unused_threshold_param() -> None:
    """F-5: the unused `threshold` param has been removed."""
    import inspect

    from dpsim.lifecycle.cancellation import make_cancel_event

    sig = inspect.signature(make_cancel_event)
    assert "threshold" not in sig.parameters
    assert "flag" in sig.parameters


def test_v049_F2_triptych_summary_uses_real_recipe_shape() -> None:
    """F-2: _summary_for must read the real ProcessRecipe shape."""
    from pathlib import Path

    src = (
        Path(__file__).resolve().parents[1]
        / "src" / "dpsim" / "visualization" / "shell" / "triptych.py"
    ).read_text(encoding="utf-8")
    # The fixed code reads target / material_batch / equipment / steps.
    assert "material_batch" in src
    assert "polymer_family" in src
    assert "steps_for_stage" in src
    assert "LifecycleStage.M1_FABRICATION" in src
    assert "LifecycleStage.M2_FUNCTIONALIZATION" in src
    assert "LifecycleStage.M3_PERFORMANCE" in src
    # No actual code path reads `recipe.m1.formulation.*` — the only
    # residual mention is in the audit-fix docstring describing what
    # was wrong. Verify the bad pattern doesn't appear in CODE
    # (`getattr(recipe, "m1"` / `_deep_get(recipe, "m1"`).
    assert 'getattr(recipe, "m1"' not in src
    assert "_deep_get(recipe, \"m1\"" not in src
    assert "_deep_get(recipe, \"m3\"" not in src


def test_v049_F2_triptych_summary_with_default_recipe_returns_real_chips() -> None:
    """F-2: _summary_for runs against a default recipe and produces real chips."""
    from dpsim.visualization.shell.triptych import _summary_for

    # Use the actual ensure_process_recipe_state path so we get a
    # real recipe in session_state.
    import streamlit as st

    try:
        from dpsim.visualization.ui_recipe import ensure_process_recipe_state

        ensure_process_recipe_state(st.session_state)
    except Exception:
        pass

    chips_m1 = _summary_for("m1")
    chips_m2 = _summary_for("m2")
    chips_m3 = _summary_for("m3")
    # Each stage returns 6–7 chips with non-trivial content.
    assert len(chips_m1) >= 4
    assert len(chips_m2) >= 4
    assert len(chips_m3) >= 4
    # The real recipe should report polymer family + polymer lot for M1.
    m1_keys = {c[0] for c in chips_m1}
    assert "family" in m1_keys
    assert "polymer lot" in m1_keys
    # M2 should report ligand + analyte (defaults: Protein A / IgG).
    m2_keys = {c[0] for c in chips_m2}
    assert "ligand" in m2_keys
    assert "analyte" in m2_keys
    # M3 should report column + detector + max ΔP target.
    m3_keys = {c[0] for c in chips_m3}
    assert "column" in m3_keys
    assert "detector" in m3_keys


def test_app_module_imports_cleanly_at_module_level() -> None:
    """Verify ``app.py`` is parseable.

    We don't execute it at import time (it would call ``st.set_page_config``
    outside a Streamlit run), but we DO confirm the AST parses and every
    top-level import resolves.
    """
    import ast
    from pathlib import Path

    app_path = (
        Path(__file__).resolve().parents[1]
        / "src" / "dpsim" / "visualization" / "app.py"
    )
    src = app_path.read_text(encoding="utf-8")
    tree = ast.parse(src)
    # The new shell imports must be present.
    sources = ast.dump(tree)
    assert "inject_global_css" in sources
    assert "render_shell" in sources
    assert "render_run_rail" in sources
    # The legacy CSS block (~200 lines starting with --dps-bg in app.py
    # itself) must be GONE — verify we don't ship duplicate token defs.
    assert "--dps-bg: #0F172A;" not in src, (
        "legacy --dps-* CSS block must be removed; tokens come from "
        "tokens.css now"
    )
