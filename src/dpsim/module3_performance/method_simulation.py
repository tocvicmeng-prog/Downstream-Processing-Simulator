"""``run_method_simulation`` — single entry point for M3 method execution.

Reference: docs/performance_recipe_protocol.md, Module M2 (A4).

Subsumes the dual-path lifecycle orchestration that v0.1.0 used:
  - ``run_chromatography_method`` for the d50 representative.
  - ``_run_dsd_downstream_screen`` for per-quantile pressure/DBC screening.

Both paths are now driven from the typed ``PerformanceRecipe`` primitive
and produce one ``MethodSimulationResult`` with a single weakest-tier
manifest roll-up. Per the v0.2.0 Q1 decision, the elute step defaults to
``run_loaded_state_elution`` (loaded-state low-pH); ``run_gradient_elution``
is dispatched only when the elute step's ``metadata['competitive_gradient']``
is True. This isolates the architectural refactor from the scientific-baseline
change for v0.2.0.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

import numpy as np

from dpsim.core.performance_recipe import PerformanceRecipe
from dpsim.datatypes import ModelEvidenceTier, ModelManifest

from .gradient import make_linear_gradient
from .hydrodynamics import ColumnGeometry
from .method import (
    ChromatographyMethodResult,
    ChromatographyMethodStep,
    run_chromatography_method,
)
from .orchestrator import (
    GradientElutionResult,
    _build_m3_chrom_manifest,
    run_gradient_elution,
)

if TYPE_CHECKING:
    from dpsim.module2_functionalization.orchestrator import FunctionalMicrosphere

_TIER_ORDER = list(ModelEvidenceTier)


# ─── Per-quantile result ─────────────────────────────────────────────────────


@dataclass
class DSDQuantileResult:
    """Per-DSD-quantile method outcome.

    ``method_result`` is None when ``recipe.dsd_policy.fast_pressure_screen``
    short-circuited the full LRM solve.
    """

    quantile: float
    mass_fraction: float
    bead_diameter_m: float
    method_result: ChromatographyMethodResult | None
    pressure_drop_Pa: float
    bed_compression_fraction: float
    dbc_10pct_mol_m3: float | None
    mass_balance_error: float | None
    weakest_tier: ModelEvidenceTier
    diagnostics: dict[str, float | str] = field(default_factory=dict)


# ─── Aggregated result ───────────────────────────────────────────────────────


@dataclass
class MethodSimulationResult:
    """Aggregated M3 result spanning the d50 method and (optional) DSD quantiles.

    Attributes:
        representative: Full method result for the d50 column.
        dsd_quantile_results: One entry per DSD quantile when DSD propagation
            was requested; empty otherwise.
        gradient_elution: Populated only when the elute step's
            ``metadata['competitive_gradient']`` opt-in is True and the recipe
            has a gradient_field-bearing elute step.
        model_manifest: Weakest-tier roll-up across representative, gradient,
            and per-quantile manifests.
        assumptions: Concatenated assumptions across all contributors.
        wet_lab_caveats: Concatenated caveats.
    """

    representative: ChromatographyMethodResult
    dsd_quantile_results: list[DSDQuantileResult]
    gradient_elution: GradientElutionResult | None
    model_manifest: ModelManifest
    assumptions: list[str]
    wet_lab_caveats: list[str]

    def as_summary(self) -> dict[str, Any]:
        """JSON-serialisable summary suitable for ProcessDossier export."""
        rep = self.representative
        load_bt = rep.load_breakthrough
        return {
            "representative": {
                "operation_count": len(rep.method_steps),
                "operability_pressure_drop_Pa": float(rep.operability.pressure_drop_Pa),
                "operability_bed_compression_fraction": float(
                    rep.operability.bed_compression_fraction
                ),
                "load_breakthrough_dbc_10pct_mol_m3": (
                    None if load_bt is None else float(load_bt.dbc_10pct)
                ),
                "load_breakthrough_mass_balance_error": (
                    None if load_bt is None else float(load_bt.mass_balance_error)
                ),
            },
            "dsd_quantiles": [
                {
                    "quantile": float(q.quantile),
                    "mass_fraction": float(q.mass_fraction),
                    "bead_diameter_m": float(q.bead_diameter_m),
                    "pressure_drop_Pa": float(q.pressure_drop_Pa),
                    "bed_compression_fraction": float(q.bed_compression_fraction),
                    "dbc_10pct_mol_m3": (
                        None if q.dbc_10pct_mol_m3 is None else float(q.dbc_10pct_mol_m3)
                    ),
                    "mass_balance_error": (
                        None if q.mass_balance_error is None else float(q.mass_balance_error)
                    ),
                    "method_simulated": q.method_result is not None,
                    "weakest_tier": q.weakest_tier.value,
                }
                for q in self.dsd_quantile_results
            ],
            "gradient_elution_simulated": self.gradient_elution is not None,
            "weakest_tier": self.model_manifest.evidence_tier.value,
            "calibration_ref": self.model_manifest.calibration_ref,
        }


# ─── Public entry point ──────────────────────────────────────────────────────


def run_method_simulation(
    recipe: PerformanceRecipe,
    *,
    microsphere: "FunctionalMicrosphere | None" = None,
    fmc: Any | None = None,
    process_state: Any | None = None,
    dsd_payload: Any | None = None,
) -> MethodSimulationResult:
    """Run the full M3 chromatography method, with optional DSD propagation.

    Args:
        recipe: Compiled M3 recipe.
        microsphere: Optional FunctionalMicrosphere; when supplied, its
            d50 / pore / mechanics override the recipe's column defaults
            for the d50 path.
        fmc: Optional FunctionalMediaContract; propagates into both the
            method-level manifest and the gradient-elution manifest.
        process_state: Optional ProcessState (or dict) with mobile-phase
            conditions for gradient-sensitive isotherms.
        dsd_payload: Optional ``BeadSizeDistributionPayload`` with quantile
            table support. Required when ``recipe.dsd_policy.run_full_method``
            is True.

    Returns:
        ``MethodSimulationResult`` with the d50 method, optional gradient
        elution result, optional per-quantile DSD results, and a weakest-tier
        manifest roll-up.

    Raises:
        ValueError: When ``recipe.dsd_policy.run_full_method`` is True but
            ``dsd_payload`` is None.
    """
    column = _column_with_microsphere(recipe.column, microsphere)
    representative = run_chromatography_method(
        column=column,
        method_steps=list(recipe.method_steps),
        fmc=fmc,
        process_state=process_state,
        max_pressure_Pa=recipe.max_pressure_drop_Pa,
        pump_pressure_limit_Pa=recipe.pump_pressure_limit_Pa,
        n_z=recipe.n_z,
        D_molecular=recipe.D_molecular,
        k_ads=recipe.k_ads,
    )

    gradient_elution = _maybe_run_gradient_elute(
        recipe=recipe,
        column=column,
        fmc=fmc,
        process_state=process_state,
    )

    dsd_results = _maybe_run_dsd(
        recipe=recipe,
        microsphere=microsphere,
        fmc=fmc,
        process_state=process_state,
        dsd_payload=dsd_payload,
    )

    manifest = _rollup_manifest(
        representative=representative,
        gradient_elution=gradient_elution,
        dsd_results=dsd_results,
        fmc=fmc,
    )

    assumptions: list[str] = list(representative.assumptions)
    wet_lab_caveats: list[str] = list(representative.wet_lab_caveats)
    if gradient_elution is not None and gradient_elution.model_manifest is not None:
        assumptions.extend(gradient_elution.model_manifest.assumptions)

    return MethodSimulationResult(
        representative=representative,
        dsd_quantile_results=dsd_results,
        gradient_elution=gradient_elution,
        model_manifest=manifest,
        assumptions=assumptions,
        wet_lab_caveats=wet_lab_caveats,
    )


# ─── Internal helpers ────────────────────────────────────────────────────────


def _column_with_microsphere(
    column: ColumnGeometry,
    microsphere: "FunctionalMicrosphere | None",
) -> ColumnGeometry:
    """Override the recipe column's particle properties with M2 microsphere state."""
    if microsphere is None:
        return column
    m1 = microsphere.m1_contract
    return ColumnGeometry(
        diameter=column.diameter,
        bed_height=column.bed_height,
        particle_diameter=m1.bead_d50,
        bed_porosity=column.bed_porosity,
        particle_porosity=m1.porosity,
        G_DN=microsphere.G_DN_updated or m1.G_DN,
        E_star=microsphere.E_star_updated or m1.E_star,
    )


def _maybe_run_gradient_elute(
    *,
    recipe: PerformanceRecipe,
    column: ColumnGeometry,
    fmc: Any | None,
    process_state: Any | None,
) -> GradientElutionResult | None:
    """Dispatch to ``run_gradient_elution`` when the recipe explicitly opts in.

    Per the v0.2.0 Q1 decision, ``has_gradient_elute()`` reports recipe intent
    only — the elute step must additionally set
    ``metadata['competitive_gradient'] = True`` to actually invoke the
    competitive-Langmuir gradient solver. Without this opt-in the recipe's
    ``gradient_field`` is purely declarative; the loaded-state elution inside
    ``run_chromatography_method`` is the active elution model.
    """
    if not recipe.has_gradient_elute():
        return None
    elute = recipe.elute_step()
    if elute is None:
        return None
    if not bool(elute.metadata.get("competitive_gradient", False)):
        return None
    load = recipe.load_step()
    if load is None:
        return None
    gradient_program = _gradient_program_from_step(elute, load)
    total_time = max(
        load.duration_s + elute.duration_s,
        recipe.total_time_s,
    )
    return run_gradient_elution(
        column=column,
        C_feed=np.array([float(load.feed_concentration_mol_m3)]),
        gradient=gradient_program,
        flow_rate=float(elute.flow_rate_m3_s),
        total_time=float(total_time),
        feed_duration=float(load.duration_s),
        n_z=recipe.n_z,
        D_molecular=recipe.D_molecular,
        k_ads=recipe.k_ads,
        fmc=fmc,
        process_state=process_state,
    )


def _gradient_program_from_step(
    elute: ChromatographyMethodStep,
    load: ChromatographyMethodStep,
):
    """Build a ``GradientProgram`` linear ramp from the elute step's gradient bounds."""
    start = elute.gradient_start
    end = elute.gradient_end
    if start is None:
        start = float(elute.buffer.pH) if elute.gradient_field.lower() == "ph" else 0.0
    if end is None:
        end = float(elute.buffer.pH) if elute.gradient_field.lower() == "ph" else 0.0
    return make_linear_gradient(
        start_val=float(start),
        end_val=float(end),
        start_time=float(load.duration_s),
        end_time=float(load.duration_s + elute.duration_s),
    )


def _maybe_run_dsd(
    *,
    recipe: PerformanceRecipe,
    microsphere: "FunctionalMicrosphere | None",
    fmc: Any | None,
    process_state: Any | None,
    dsd_payload: Any | None,
) -> list[DSDQuantileResult]:
    """Per-DSD-quantile execution (full method or fast pressure screen).

    v0.6.0 (E2): when ``recipe.dsd_policy.run_full_method=True`` and
    ``recipe.dsd_policy.n_jobs > 1``, the per-quantile full-method runs are
    dispatched in parallel via ``joblib.Parallel`` with the loky backend. The
    fast_pressure_screen path is always serial (its algebraic cost is far
    below joblib's per-task overhead). ``n_jobs=1`` (default) preserves
    bit-identical serial behaviour from v0.5.0.
    """
    policy = recipe.dsd_policy
    if not policy.run_full_method and not policy.fast_pressure_screen:
        return []
    if policy.run_full_method and dsd_payload is None:
        raise ValueError(
            "PerformanceRecipe.dsd_policy.run_full_method=True requires a "
            "dsd_payload from M1; got None."
        )
    if dsd_payload is None:
        return []
    rows = _quantile_rows(dsd_payload, policy.quantiles)

    if policy.run_full_method:
        column_qs = [
            _column_for_quantile(recipe.column, microsphere, row["diameter_m"])
            for row in rows
        ]
        method_kwargs_per_row = [
            dict(
                column=column_q,
                method_steps=list(recipe.method_steps),
                fmc=fmc,
                process_state=process_state,
                max_pressure_Pa=recipe.max_pressure_drop_Pa,
                pump_pressure_limit_Pa=recipe.pump_pressure_limit_Pa,
                n_z=recipe.n_z,
                D_molecular=recipe.D_molecular,
                k_ads=recipe.k_ads,
            )
            for column_q in column_qs
        ]
        method_results = _run_methods_parallel_or_serial(
            method_kwargs_per_row, n_jobs=policy.n_jobs
        )
        return [
            _dsd_result_from_method(row, column_q, method_q)
            for row, column_q, method_q in zip(rows, column_qs, method_results)
        ]
    # fast_pressure_screen path — algebraic, kept serial.
    out: list[DSDQuantileResult] = []
    for row in rows:
        column_q = _column_for_quantile(recipe.column, microsphere, row["diameter_m"])
        out.append(_dsd_result_fast_screen(recipe, row, column_q, fmc))
    return out


def _run_methods_parallel_or_serial(
    kwargs_per_row: list[dict[str, Any]],
    *,
    n_jobs: int,
) -> list[ChromatographyMethodResult]:
    """Dispatch a list of run_chromatography_method calls serial or via joblib.

    v0.6.0 (E2): ``n_jobs == 1`` keeps the v0.5.0 serial behaviour bit-identical.
    ``n_jobs > 1`` uses ``joblib.Parallel`` with the loky backend (process-based)
    so each per-quantile LRM solve runs in its own subprocess. ImportError on
    joblib falls back gracefully to serial.
    """
    if n_jobs == 1 or len(kwargs_per_row) <= 1:
        return [_run_method_worker(kwargs) for kwargs in kwargs_per_row]
    try:
        from joblib import Parallel, delayed
    except ImportError:  # pragma: no cover — joblib is pinned in pyproject
        return [_run_method_worker(kwargs) for kwargs in kwargs_per_row]
    return list(
        Parallel(n_jobs=n_jobs, backend="loky")(
            delayed(_run_method_worker)(kwargs) for kwargs in kwargs_per_row
        )
    )


def _run_method_worker(kwargs: dict[str, Any]) -> ChromatographyMethodResult:
    """Module-level worker for joblib pickling.

    Joblib's loky backend pickles the callable + arguments into a worker
    subprocess. This wrapper exists so the dispatch is a stable top-level
    function reference rather than a closure (which loky cannot pickle).
    """
    return run_chromatography_method(**kwargs)


def _quantile_rows(dsd_payload: Any, quantiles: tuple[float, ...]) -> list[dict[str, float]]:
    """Use ``dsd_payload.quantile_table`` when available, else single-row fallback."""
    quantile_table = getattr(dsd_payload, "quantile_table", None)
    if callable(quantile_table):
        rows = quantile_table(list(quantiles)) or []
        return [
            {
                "quantile": float(r.get("quantile", 0.0)),
                "diameter_m": float(r.get("diameter_m", 0.0)),
                "mass_fraction": float(r.get("mass_fraction", 0.0)),
            }
            for r in rows
        ]
    diameter = float(getattr(dsd_payload, "d50_m", 0.0))
    return [
        {"quantile": 0.5, "diameter_m": diameter, "mass_fraction": 1.0}
    ]


def _column_for_quantile(
    base: ColumnGeometry,
    microsphere: "FunctionalMicrosphere | None",
    diameter_m: float,
) -> ColumnGeometry:
    """Build a per-quantile column varying particle_diameter only."""
    if microsphere is not None:
        m1 = microsphere.m1_contract
        return ColumnGeometry(
            diameter=base.diameter,
            bed_height=base.bed_height,
            particle_diameter=float(diameter_m) if diameter_m > 0 else m1.bead_d50,
            bed_porosity=base.bed_porosity,
            particle_porosity=m1.porosity,
            G_DN=microsphere.G_DN_updated or m1.G_DN,
            E_star=microsphere.E_star_updated or m1.E_star,
        )
    return ColumnGeometry(
        diameter=base.diameter,
        bed_height=base.bed_height,
        particle_diameter=float(diameter_m) if diameter_m > 0 else base.particle_diameter,
        bed_porosity=base.bed_porosity,
        particle_porosity=base.particle_porosity,
        G_DN=base.G_DN,
        E_star=base.E_star,
    )


def _dsd_result_from_method(
    row: dict[str, float],
    column: ColumnGeometry,
    method: ChromatographyMethodResult,
) -> DSDQuantileResult:
    load_bt = method.load_breakthrough
    pressure = float(method.operability.pressure_drop_Pa)
    compression = float(method.operability.bed_compression_fraction)
    dbc_10 = None if load_bt is None else float(load_bt.dbc_10pct)
    mb = None if load_bt is None else float(load_bt.mass_balance_error)
    tier = (
        method.model_manifest.evidence_tier
        if method.model_manifest is not None
        else ModelEvidenceTier.SEMI_QUANTITATIVE
    )
    return DSDQuantileResult(
        quantile=row["quantile"],
        mass_fraction=row["mass_fraction"],
        bead_diameter_m=row["diameter_m"],
        method_result=method,
        pressure_drop_Pa=pressure,
        bed_compression_fraction=compression,
        dbc_10pct_mol_m3=dbc_10,
        mass_balance_error=mb,
        weakest_tier=tier,
        diagnostics={"path": "full_method"},
    )


def _dsd_result_fast_screen(
    recipe: PerformanceRecipe,
    row: dict[str, float],
    column: ColumnGeometry,
    fmc: Any | None,
) -> DSDQuantileResult:
    """Cheap algebraic pressure + bed compression screen — no LRM solve."""
    load = recipe.load_step()
    flow_rate = float(load.flow_rate_m3_s) if load is not None else 1e-8
    pressure = float(column.pressure_drop(flow_rate))
    compression = float(column.bed_compression_fraction(pressure))
    fmc_tier = (
        getattr(getattr(fmc, "model_manifest", None), "evidence_tier", None)
        or ModelEvidenceTier.SEMI_QUANTITATIVE
    )
    return DSDQuantileResult(
        quantile=row["quantile"],
        mass_fraction=row["mass_fraction"],
        bead_diameter_m=row["diameter_m"],
        method_result=None,
        pressure_drop_Pa=pressure,
        bed_compression_fraction=compression,
        dbc_10pct_mol_m3=None,
        mass_balance_error=None,
        weakest_tier=fmc_tier,
        diagnostics={"path": "fast_pressure_screen"},
    )


def _rollup_manifest(
    *,
    representative: ChromatographyMethodResult,
    gradient_elution: GradientElutionResult | None,
    dsd_results: list[DSDQuantileResult],
    fmc: Any | None,
) -> ModelManifest:
    """Weakest-tier roll-up across all M3 contributors."""
    contributors: list[ModelManifest] = []
    if representative.model_manifest is not None:
        contributors.append(representative.model_manifest)
    if gradient_elution is not None and gradient_elution.model_manifest is not None:
        contributors.append(gradient_elution.model_manifest)
    for q in dsd_results:
        if q.method_result is not None and q.method_result.model_manifest is not None:
            contributors.append(q.method_result.model_manifest)

    if not contributors:
        return _build_m3_chrom_manifest(
            model_basename="M3.method_simulation.empty",
            isotherm=None,
            fmc=fmc,
            worst_mass_balance_error=0.0,
            diagnostics_extra={"contributors": 0},
        )

    weakest = contributors[0].evidence_tier
    weakest_idx = _TIER_ORDER.index(weakest)
    for m in contributors[1:]:
        idx = _TIER_ORDER.index(m.evidence_tier)
        if idx > weakest_idx:
            weakest = m.evidence_tier
            weakest_idx = idx

    worst_mb = 0.0
    if representative.load_breakthrough is not None:
        worst_mb = max(worst_mb, float(representative.load_breakthrough.mass_balance_error))
    if (
        representative.loaded_elution is not None
        and representative.loaded_elution.mass_balance_error is not None
    ):
        worst_mb = max(worst_mb, float(representative.loaded_elution.mass_balance_error))
    if gradient_elution is not None and len(gradient_elution.mass_balance_errors) > 0:
        worst_mb = max(worst_mb, float(np.max(gradient_elution.mass_balance_errors)))
    for q in dsd_results:
        if q.mass_balance_error is not None:
            worst_mb = max(worst_mb, float(q.mass_balance_error))

    calibration_ref = ""
    for m in contributors:
        if m.calibration_ref:
            calibration_ref = m.calibration_ref
            break

    assumptions = [
        f"M3 method simulation rolls up the weakest tier ({weakest.value}) "
        f"across {len(contributors)} contributor(s).",
    ]
    diagnostics: dict[str, Any] = {
        "contributors": len(contributors),
        "dsd_quantile_count": len(dsd_results),
        "gradient_elution_included": gradient_elution is not None,
        "max_mass_balance_error": float(worst_mb),
    }

    return ModelManifest(
        model_name="M3.method_simulation",
        evidence_tier=weakest,
        valid_domain={},
        calibration_ref=calibration_ref,
        assumptions=assumptions,
        diagnostics=diagnostics,
    )


__all__ = [
    "DSDQuantileResult",
    "MethodSimulationResult",
    "run_method_simulation",
]
