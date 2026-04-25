"""PerformanceRecipe — typed compiled view over the M3 portion of a ProcessRecipe.

This module is the canonical input contract to ``run_method_simulation`` (added
in module A4 of the v0.2.0 milestone). It owns the column geometry, the executable
chromatography method-step list, the load-feed context, the DSD propagation
policy, and the operability gates that the lifecycle orchestrator otherwise
scatters across function arguments.

The data model is decoupled from ``dpsim.lifecycle`` at runtime: only the
optional builder ``performance_recipe_from_resolved`` reads
``LifecycleResolvedInputs``, and that reference is forward-only via TYPE_CHECKING
so the ``dpsim.core`` layer stays free of lifecycle imports.

Reference: docs/performance_recipe_protocol.md, Module M1 (A1).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from dpsim.module3_performance.hydrodynamics import ColumnGeometry
from dpsim.module3_performance.method import (
    ChromatographyMethodStep,
    ChromatographyOperation,
)

if TYPE_CHECKING:
    from dpsim.lifecycle.recipe_resolver import LifecycleResolvedInputs


@dataclass(frozen=True)
class DSDPolicy:
    """How M3 should consume M1's representative DSD quantiles.

    Attributes:
        quantiles: Quantile fractions in (0, 1). Default ``(0.10, 0.50, 0.90)``
            samples the lower tail, median, and upper tail of the DSD.
        run_full_method: When True, ``run_method_simulation`` runs the full
            pack -> equilibrate -> load -> wash -> elute method per quantile.
            When False (default), only the d50 representative gets the full
            method.
        fast_pressure_screen: When True, per-quantile runs use the cheap
            algebraic pressure screen instead of the full LRM. Has effect only
            when ``run_full_method`` is False (the screen is the alternative
            to the full method). Default True so DSD pressure-spread reporting
            stays cheap when the full per-quantile method is not requested.
        n_jobs: Reserved for joblib-parallel per-quantile execution. Not
            consumed in v0.2.0; kept on the API for forward compatibility
            with the v0.4.0 bin-resolved DSD work.
        monte_carlo_n_samples: v0.3.0 (G3) — number of Monte-Carlo posterior
            samples for LRM uncertainty propagation. ``0`` (default) disables
            MC entirely and preserves bit-identical legacy behaviour. ``> 0``
            requires both a ``posterior_samples`` and an ``mc_lrm_solver`` to
            be passed to ``run_method_simulation`` for the MC path to fire.
        monte_carlo_n_seeds: v0.3.0 (G3) — number of independent seed-wise
            sub-runs for inter-seed posterior overlap (SA-Q3 / D-047). Default
            4 per the architect spec. Has effect only when
            ``monte_carlo_n_samples > 0``.
        monte_carlo_parameter_clips: v0.3.0 (G3) — optional Tier-2 clipping
            (SA-Q1 / D-046). Mapping ``{parameter_name: (lo, hi)}``. Has
            effect only when ``monte_carlo_n_samples > 0``.
    """

    quantiles: tuple[float, ...] = (0.10, 0.50, 0.90)
    run_full_method: bool = False
    fast_pressure_screen: bool = True
    n_jobs: int = 1
    monte_carlo_n_samples: int = 0
    monte_carlo_n_seeds: int = 4
    monte_carlo_parameter_clips: dict[str, tuple[float, float]] | None = None


@dataclass
class PerformanceRecipe:
    """Compiled M3 method specification.

    Built once per lifecycle run from a fully resolved ``ProcessRecipe`` via
    ``performance_recipe_from_resolved``. Once constructed, this object is the
    single source of truth for column geometry, method steps, feed conditions,
    DSD propagation policy, and operability gates consumed by
    ``run_method_simulation``.

    Attributes:
        column: Packed-bed geometry and hydraulic parameters.
        method_steps: Ordered list of pack -> equilibrate -> load -> wash ->
            elute operations resolved from the recipe.
        feed_concentration_mol_m3: Load-step feed concentration [mol/m3].
        feed_duration_s: Load-step duration [s].
        total_time_s: Total simulation horizon [s]; must satisfy
            ``total_time_s >= feed_duration_s``.
        n_z: Axial discretisation count for LRM solvers.
        dsd_policy: How DSD quantiles propagate from M1 into M3.
        max_pressure_drop_Pa: Method-target pressure ceiling [Pa].
        pump_pressure_limit_Pa: Hard pump-side limit [Pa].
        D_molecular: Solute molecular diffusivity [m^2/s].
        k_ads: Adsorption rate constant [1/s].
        notes: Free-form provenance / annotation.
    """

    column: ColumnGeometry
    method_steps: list[ChromatographyMethodStep]
    feed_concentration_mol_m3: float
    feed_duration_s: float
    total_time_s: float
    n_z: int = 30
    dsd_policy: DSDPolicy = field(default_factory=DSDPolicy)
    max_pressure_drop_Pa: float = 3.0e5
    pump_pressure_limit_Pa: float = 3.0e5
    D_molecular: float = 7.0e-11
    k_ads: float = 100.0
    notes: str = ""

    def load_step(self) -> ChromatographyMethodStep | None:
        """Return the first LOAD step, or None if absent."""
        return self._first_step(ChromatographyOperation.LOAD)

    def elute_step(self) -> ChromatographyMethodStep | None:
        """Return the first ELUTE step, or None if absent."""
        return self._first_step(ChromatographyOperation.ELUTE)

    def pack_step(self) -> ChromatographyMethodStep | None:
        """Return the first PACK step, or None if absent."""
        return self._first_step(ChromatographyOperation.PACK)

    def has_gradient_elute(self) -> bool:
        """True iff the first ELUTE step declares a non-empty ``gradient_field``.

        Reports recipe-level *intent* only. The dispatch decision in
        ``run_method_simulation`` is gated separately (per protocol §11 Q1
        decision: v0.2.0 keeps ``run_loaded_state_elution`` as default and
        requires an explicit recipe-level opt-in for ``run_gradient_elution``).
        """
        elute = self.elute_step()
        if elute is None:
            return False
        return bool(elute.gradient_field and elute.gradient_field.strip())

    def _first_step(
        self, operation: ChromatographyOperation
    ) -> ChromatographyMethodStep | None:
        for step in self.method_steps:
            if step.operation == operation:
                return step
        return None


def performance_recipe_from_resolved(
    resolved: LifecycleResolvedInputs,
    *,
    dsd_policy: DSDPolicy | None = None,
) -> PerformanceRecipe:
    """Build a ``PerformanceRecipe`` from a ``LifecycleResolvedInputs``.

    The resolved recipe must contain at minimum a PACK step and a LOAD step;
    otherwise a ``ValueError`` is raised. The clean-slate primitive
    intentionally rejects degenerate states that the looser legacy lifecycle
    path silently accepted.

    Args:
        resolved: Output of ``resolve_lifecycle_inputs(recipe)``.
        dsd_policy: DSD propagation policy. Uses the default ``DSDPolicy()``
            when None.

    Returns:
        A populated ``PerformanceRecipe``.

    Raises:
        ValueError: When the resolved recipe is missing a PACK or LOAD step.
    """
    method_steps = list(resolved.m3_method_steps)
    operations = {step.operation for step in method_steps}
    missing: list[str] = []
    if ChromatographyOperation.PACK not in operations:
        missing.append("PACK")
    if ChromatographyOperation.LOAD not in operations:
        missing.append("LOAD")
    if missing:
        present = [s.operation.value for s in method_steps] or "none"
        raise ValueError(
            f"PerformanceRecipe requires {', '.join(missing)} step(s); "
            f"resolved recipe contains: {present}"
        )

    return PerformanceRecipe(
        column=resolved.column,
        method_steps=method_steps,
        feed_concentration_mol_m3=resolved.m3_feed_concentration,
        feed_duration_s=resolved.m3_feed_duration,
        total_time_s=resolved.m3_total_time,
        n_z=resolved.m3_n_z,
        dsd_policy=dsd_policy if dsd_policy is not None else DSDPolicy(),
        max_pressure_drop_Pa=resolved.max_pressure_drop_Pa,
        pump_pressure_limit_Pa=resolved.pump_pressure_limit_Pa,
    )


__all__ = [
    "DSDPolicy",
    "PerformanceRecipe",
    "performance_recipe_from_resolved",
]
