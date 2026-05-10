"""Inverse Design / Optimization tab — top-level UI for the BO engine.

B-5c KEYSTONE / W-075 — v0.8.7. Closes the v0.8.5 audit defect S-7 +
A-6: ``OptimizationEngine`` was CLI-only at v0.8.6, reachable only via
``python -m dpsim`` subcommands. The dashboard now hosts a top-level
*Inverse Design* tab where a wet-lab user can ask the simulator
*"given my target d32 / pore size / modulus + my pressure budget,
find the recipe that meets all targets"*.

Tier framing: results render at SEMI_QUANTITATIVE per ADR-007 — the
recommended operating point reflects the GP's posterior over the M1
process model, NOT a wet-lab calibration. Promotion to
CALIBRATED_LOCAL requires the wet-lab handshake.

The optimization extra (``pip install dpsim[optimization]``) is a hard
prerequisite for this tab — torch + botorch + gpytorch are not in the
base install. The tab gracefully degrades to an install-instructions
banner when the import fails.
"""

from __future__ import annotations

from typing import Any, Optional

import streamlit as st

from dpsim.core.decision_grade import OutputType
from dpsim.datatypes import ModelEvidenceTier
from dpsim.visualization.decision_grade_render import render_metric


def _check_optimization_extra_available() -> tuple[bool, Optional[str]]:
    """Return (available, error_msg). When False, the UI shows an install banner."""
    try:
        import torch  # noqa: F401  (verifying availability)
        from dpsim.optimization.engine import OptimizationEngine  # noqa: F401
        return True, None
    except ImportError as exc:
        return False, str(exc)


def _render_install_banner() -> None:
    """Banner shown when the optimization extra is not installed."""
    st.warning(
        "The Inverse Design tab requires the optional `optimization` extra "
        "(torch + botorch + gpytorch — ~1.4 GB combined; not in the base "
        "install). To enable, run from the repo root:"
    )
    st.code(
        "pip install -e '.[optimization]'",
        language="bash",
    )
    st.caption(
        "After installation, restart the Streamlit app. The pinned versions "
        "(`botorch~=0.17.2`, `gpytorch~=1.15.2`, `torch~=2.11.0`) match "
        "ADR-002 — the smoke test exercises a duck-typed call site that "
        "is only stable inside this version range."
    )


def _render_target_spec_inputs() -> Any:
    """Render the TargetSpec parameter inputs.

    Returns a TargetSpec or None when the user has not enabled at least
    one target dimension.
    """
    from dpsim.optimization.objectives import TargetSpec

    st.markdown("### Targets — what does a *good* recipe deliver?")
    st.caption(
        "Each target pairs a value with a tolerance. Disabled rows are "
        "removed from the objective vector. At least one dimension must "
        "be active; the BO uses tolerance-normalised distances so every "
        "dimension lands on a comparable scale."
    )

    use_d32 = st.checkbox("Target d32 (Sauter mean droplet diameter)", value=True)
    d32_target = d32_tol = None
    if use_d32:
        cols = st.columns(2)
        d32_target = cols[0].number_input(
            "d32 target (µm)", min_value=0.5, max_value=200.0,
            value=2.0, step=0.5, key="opt_d32_t",
        )
        d32_tol = cols[1].number_input(
            "d32 tolerance (µm)", min_value=0.05, max_value=50.0,
            value=0.2, step=0.05, key="opt_d32_tol",
        )

    use_pore = st.checkbox("Target pore size", value=True)
    pore_target = pore_tol = None
    if use_pore:
        cols = st.columns(2)
        pore_target = cols[0].number_input(
            "Pore target (nm)", min_value=1.0, max_value=1000.0,
            value=80.0, step=5.0, key="opt_pore_t",
        )
        pore_tol = cols[1].number_input(
            "Pore tolerance (nm)", min_value=1.0, max_value=200.0,
            value=10.0, step=1.0, key="opt_pore_tol",
        )

    use_G_DN = st.checkbox("Target G_DN (shear modulus)", value=False)
    G_DN_target = G_DN_log10_tol = None
    if use_G_DN:
        cols = st.columns(2)
        G_DN_target = cols[0].number_input(
            "G_DN target (kPa)", min_value=0.5, max_value=10000.0,
            value=50.0, step=5.0, key="opt_GDN_t",
        )
        G_DN_log10_tol = cols[1].number_input(
            "G_DN log10 tolerance",
            min_value=0.05, max_value=2.0,
            value=0.3, step=0.05, key="opt_GDN_tol",
            help="distance = |log10(G_DN) − log10(target)| / log10_tol",
        )

    if not (use_d32 or use_pore or use_G_DN):
        return None
    return TargetSpec(
        d32_target=(d32_target * 1e-6) if d32_target is not None else None,
        d32_tol=(d32_tol * 1e-6) if d32_tol is not None else None,
        pore_target=(pore_target * 1e-9) if pore_target is not None else None,
        pore_tol=(pore_tol * 1e-9) if pore_tol is not None else None,
        G_DN_target=(G_DN_target * 1e3) if G_DN_target is not None else None,
        G_DN_log10_tol=G_DN_log10_tol,
    )


def _render_optimization_results(state: Any) -> None:
    """Show the campaign's best-recipe summary."""
    import numpy as np
    from dpsim.optimization.analysis import pareto_candidate_rankings

    st.markdown("### Recommended recipes")
    st.caption(
        "Best predicted is objective-only. Best actionable also requires "
        "decision-grade point claims and a passing pressure-feasibility screen."
    )

    Y = np.asarray(state.pareto_Y if len(state.pareto_Y) else state.Y_observed, dtype=float)
    if Y.size == 0:
        st.warning("Optimisation produced no observations.")
        return
    rankings = pareto_candidate_rankings(state) if len(state.pareto_Y) else {
        "best_predicted": {
            "candidate_index": int(np.argmin(np.sum(Y, axis=1))),
            "objective_sum": float(np.min(np.sum(Y, axis=1))),
            "evidence_tier": ModelEvidenceTier.SEMI_QUANTITATIVE.value,
            "missing_calibration_count": 0,
            "pressure_status": "not_evaluated",
            "actionability_gaps": ["pressure_feasibility_not_evaluated"],
        },
        "best_actionable": None,
    }
    best_predicted = rankings["best_predicted"]
    if best_predicted is None:
        st.warning("No Pareto candidates were available for ranking.")
        return
    best_idx = int(best_predicted["candidate_index"])
    X_source = state.pareto_X if len(state.pareto_X) else state.X_observed
    X_ss = np.asarray(X_source[best_idx], dtype=float)
    obj = Y[best_idx]

    ranking_rows = [
        {
            "Ranking": "Best predicted",
            "Candidate": best_idx,
            "Objective sum": f"{float(best_predicted['objective_sum']):.3f}",
            "Evidence tier": best_predicted["evidence_tier"],
            "Pressure": best_predicted["pressure_status"],
            "Actionability gaps": ", ".join(best_predicted["actionability_gaps"]) or "none",
        }
    ]
    best_actionable = rankings["best_actionable"]
    if best_actionable is not None:
        ranking_rows.append({
            "Ranking": "Best actionable",
            "Candidate": int(best_actionable["candidate_index"]),
            "Objective sum": f"{float(best_actionable['objective_sum']):.3f}",
            "Evidence tier": best_actionable["evidence_tier"],
            "Pressure": best_actionable["pressure_status"],
            "Actionability gaps": ", ".join(best_actionable["actionability_gaps"]) or "none",
        })
    else:
        ranking_rows.append({
            "Ranking": "Best actionable",
            "Candidate": "none",
            "Objective sum": "n/a",
            "Evidence tier": "n/a",
            "Pressure": "n/a",
            "Actionability gaps": "calibration and pressure gates not closed",
        })
    st.dataframe(ranking_rows, width="stretch", hide_index=True)

    objective_outputs = (
        OutputType.D32,
        OutputType.PORE_SIZE,
        OutputType.MODULUS,
    )
    cols = st.columns(min(3, len(obj)))
    for i, val in enumerate(obj):
        output_type = objective_outputs[min(i, len(objective_outputs) - 1)]
        render_metric(
            f"obj {i+1}",
            value=float(val),
            output_type=output_type,
            tier=ModelEvidenceTier.SEMI_QUANTITATIVE,
            unit="objective",
            container=cols[i % len(cols)],
            help="Tolerance-normalised objective score used for BO reporting.",
        )

    st.markdown("**Search-space coordinates (best predicted Pareto candidate)**")
    st.caption(
        "7-D normalised process space; 0–1 per dim. Map back to physical "
        "via the engine's _from_search_space helper for use at the bench."
    )
    st.dataframe(
        [
            {"coordinate": f"x[{i}]", "normalized_value": f"{float(v):.3f}"}
            for i, v in enumerate(X_ss)
        ],
        width="stretch",
        hide_index=True,
    )

    st.caption(
        f"n_observations = {len(state.Y_observed)} (n_initial + BO iterations)"
    )


def render_tab_optimization() -> None:
    """Top-level Inverse Design tab.

    Surfaces the OptimizationEngine for in-app inverse design / robust
    BO. Closes audit defects S-7 / A-6 / U-20 — the single highest
    operator-impact orphan at v0.8.6.
    """
    st.header("Inverse Design / Optimization")
    st.caption(
        "Asks the simulator: *given my targets and constraints, what "
        "recipe meets all of them?* Multi-objective Bayesian optimisation "
        "over the 7-dimensional M1 process space. Results SEMI_QUANTITATIVE "
        "per ADR-007 — wet-lab calibration required for tier promotion."
    )

    available, err = _check_optimization_extra_available()
    if not available:
        _render_install_banner()
        with st.expander("Why is the optimization extra not in the base install?"):
            st.markdown(
                "torch + botorch + gpytorch ship in the optional `optimization` "
                "extra to keep the base install lean (~50 MB without, ~1.4 GB "
                "with). Per ADR-002 the stack is pinned: minor bumps require "
                "re-verifying the FastNondominatedPartitioning duck-typing "
                "smoke test."
            )
            if err:
                st.caption(f"(import diagnostic: `{err}`)")
        return

    target_spec = _render_target_spec_inputs()
    if target_spec is None:
        st.info("Enable at least one target above to configure a campaign.")
        return

    st.markdown("### Campaign settings")
    cols = st.columns(3)
    n_initial = cols[0].slider(
        "Initial Sobol points", min_value=4, max_value=40,
        value=10, step=2, key="opt_n_init",
        help="Initial design before BO starts; ≥ 4 recommended.",
    )
    max_iter = cols[1].slider(
        "BO iterations", min_value=2, max_value=50,
        value=8, step=2, key="opt_max_iter",
        help=(
            "Each iteration runs one full M1 simulation (5–30 s). "
            "Plan ~3 minutes for 10 + 8."
        ),
    )
    use_robust = cols[2].checkbox(
        "Robust mean-variance",
        value=False,
        key="opt_robust",
        help="Sample-then-aggregate robust BO (ADR-002 F4 path).",
    )

    run = st.button("Run optimisation campaign", type="primary", key="opt_run")
    if not run and st.session_state.get("opt_state") is None:
        st.caption("Configure targets + iterations and press Run.")
        return

    if run:
        try:
            from dpsim.optimization.engine import OptimizationEngine
            engine = OptimizationEngine(
                n_initial=int(n_initial),
                max_iterations=int(max_iter),
                target_spec=target_spec,
                robust_variance_weight=(0.5 if use_robust else 0.0),
                robust_n_samples=(5 if use_robust else 0),
            )
            with st.spinner(
                f"Running {n_initial} initial + {max_iter} BO iterations — "
                "stay on this page until the spinner clears."
            ):
                state = engine.run()
            st.session_state["opt_state"] = state
            st.success(
                f"Campaign complete. {len(state.Y_observed)} observations recorded."
            )
        except Exception as exc:  # noqa: BLE001 — surface engine errors
            st.error(f"Optimisation failed: {exc!r}")
            return

    state_in_session: Any = st.session_state.get("opt_state")
    if state_in_session is not None:
        _render_optimization_results(state_in_session)
        # Tier-banner caption (we do not call render_tier_banner here since
        # that's mounted at app top-of-page; we surface the per-result tier
        # explicitly so the operator sees it next to the recipe).
        st.caption(
            f"Result tier: **{ModelEvidenceTier.SEMI_QUANTITATIVE.value}**. "
            "Promotion to CALIBRATED_LOCAL requires wet-lab confirmation of "
            "the recommended recipe."
        )


__all__ = ["render_tab_optimization"]
