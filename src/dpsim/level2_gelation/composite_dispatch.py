"""v9.2 M0b A2.5 — Composite L2 dispatch by polymer family.

A thin router that dispatches L2 gelation to the appropriate solver
based on the ``polymer_family`` attribute of MaterialProperties.

This module is **purely additive** — it does NOT replace the legacy
``solve_gelation`` entry point in ``solver.py``. Existing pipeline
code that calls ``solve_gelation`` directly continues to work unchanged
(the AGAROSE_CHITOSAN, AGAROSE_DEXTRAN-future, and any other family
that the legacy solver knows about route through that path).

Pipeline orchestrator code that wants to take advantage of the new
v9.2 Tier-1 family solvers can call ``solve_gelation_by_family`` from
this module instead — it dispatches to:

  - ``solve_gelation`` for AGAROSE_CHITOSAN (legacy / golden master)
  - ``solve_agarose_only_gelation`` for AGAROSE
  - ``solve_chitosan_only_gelation`` for CHITOSAN
  - ``solve_dextran_ech_gelation`` for DEXTRAN

Tier-2 placeholder families raise NotImplementedError with a clear
"v9.3 work — see Tier-2 roadmap" message.

The dispatcher enforces the CLAUDE.md `.value`-comparison rule for
PolymerFamily — never use ``is`` or identity comparison.
"""

from __future__ import annotations

import logging

from ..datatypes import (
    GelationResult,
    GelationTimingResult,
    MaterialProperties,
    PolymerFamily,
    SimulationParameters,
)

logger = logging.getLogger(__name__)


def solve_gelation_by_family(
    params: SimulationParameters,
    props: MaterialProperties,
    R_droplet: float = 1.0e-6,
    mode: str = "empirical",
    timing: GelationTimingResult | None = None,
) -> GelationResult:
    """Route L2 gelation to the appropriate per-family solver.

    Parameters
    ----------
    params, props : SimulationParameters, MaterialProperties
    R_droplet : float
        Microsphere radius [m].
    mode : str
        Solver mode (``"empirical"`` is universal; mechanistic modes
        are family-specific).
    timing : GelationTimingResult, optional

    Returns
    -------
    GelationResult

    Raises
    ------
    NotImplementedError
        If the family is a Tier-2 placeholder or any other family
        without a v9.2 solver. The orchestrator pipeline catches this
        and produces a "calibration pending" UI message.
    ValueError
        If the family is unrecognised entirely.
    """
    fam_value = props.polymer_family.value

    # ── v9.1 / Tier-1 families with implemented solvers ───────────────
    if fam_value == PolymerFamily.AGAROSE_CHITOSAN.value:
        # Legacy path — preserved bit-for-bit.
        from .solver import solve_gelation
        return solve_gelation(
            params=params, props=props, R_droplet=R_droplet,
            mode=mode, timing=timing,
        )

    if fam_value == PolymerFamily.AGAROSE.value:
        # v9.2 A2.2 — chitosan-free agarose
        from .agarose_only import solve_agarose_only_gelation
        return solve_agarose_only_gelation(
            params=params, props=props, R_droplet=R_droplet,
            mode=mode, timing=timing,
        )

    if fam_value == PolymerFamily.CHITOSAN.value:
        # v9.2 A2.3 — chitosan-only ionotropic / covalent
        from .chitosan_only import solve_chitosan_only_gelation
        return solve_chitosan_only_gelation(
            params=params, props=props, R_droplet=R_droplet,
            mode=mode, timing=timing,
        )

    if fam_value == PolymerFamily.DEXTRAN.value:
        # v9.2 A2.4 — Sephadex-class ECH-crosslinked dextran
        from .dextran_ech import solve_dextran_ech_gelation
        return solve_dextran_ech_gelation(
            params=params, props=props, R_droplet=R_droplet,
            mode=mode, timing=timing,
        )

    if fam_value == PolymerFamily.AMYLOSE.value:
        # v9.2 M8 B9.2 — amylose is structurally analogous to dextran
        # for bead-formation purposes (α-1,4-glucan crosslinked with
        # ECH or epichlorohydrin). The downstream M3 pipeline treats
        # the material itself as the affinity ligand (material_as_ligand
        # pattern). For L2 gelation, delegate to the dextran-ECH solver
        # with a re-tagged manifest indicating amylose provenance.
        from dataclasses import replace as _dc_replace

        from .dextran_ech import solve_dextran_ech_gelation
        # Sandbox: temporarily present as DEXTRAN to satisfy the
        # solver's family check, then re-tag the result.
        props_sandbox = _dc_replace(props, polymer_family=PolymerFamily.DEXTRAN)
        result = solve_dextran_ech_gelation(
            params=params, props=props_sandbox, R_droplet=R_droplet,
            mode=mode, timing=timing,
        )
        # Re-tag for amylose
        new_manifest = _dc_replace(
            result.model_manifest,
            model_name="L2.amylose_mbp.semi_quantitative_v9_2",
            assumptions=list(result.model_manifest.assumptions) + [
                "Amylose bead L2 gelation modeled by analogy to "
                "Sephadex-class crosslinked dextran (same ECH alkaline "
                "chemistry, same pore-size scaling). Material-as-ligand "
                "(B9) pattern applied at M3 binding stage, not L2.",
            ],
        )
        return _dc_replace(
            result,
            model_tier="amylose_mbp_via_dextran_v9_2",
            model_manifest=new_manifest,
        )

    # ── Other v9.1 families that have their own pipeline branches ────
    # These do NOT go through this dispatcher in the orchestrator —
    # the orchestrator catches them at run_single() and routes to
    # _run_alginate / _run_cellulose / _run_plga directly. If they DO
    # somehow reach this function, raise a clear error.
    if fam_value in {
        PolymerFamily.ALGINATE.value,
        PolymerFamily.CELLULOSE.value,
        PolymerFamily.PLGA.value,
    }:
        raise ValueError(
            f"Family {fam_value!r} has its own pipeline branch in "
            f"pipeline/orchestrator.py (_run_alginate, _run_cellulose, "
            f"_run_plga). Do NOT call solve_gelation_by_family for these "
            f"families — they bypass L2 dispatch."
        )

    # ── v9.3 Tier-2 promoted families ────────────────────────────────
    if fam_value == PolymerFamily.HYALURONATE.value:
        from .tier2_families import solve_hyaluronate_gelation
        return solve_hyaluronate_gelation(
            params=params, props=props, R_droplet=R_droplet,
            mode=mode, timing=timing,
        )

    if fam_value == PolymerFamily.KAPPA_CARRAGEENAN.value:
        from .tier2_families import solve_kappa_carrageenan_gelation
        return solve_kappa_carrageenan_gelation(
            params=params, props=props, R_droplet=R_droplet,
            mode=mode, timing=timing,
        )

    if fam_value == PolymerFamily.AGAROSE_DEXTRAN.value:
        from .tier2_families import solve_agarose_dextran_core_shell_gelation
        return solve_agarose_dextran_core_shell_gelation(
            params=params, props=props, R_droplet=R_droplet,
            mode=mode, timing=timing,
        )

    if fam_value == PolymerFamily.AGAROSE_ALGINATE.value:
        from .tier2_families import solve_agarose_alginate_ipn_gelation
        return solve_agarose_alginate_ipn_gelation(
            params=params, props=props, R_droplet=R_droplet,
            mode=mode, timing=timing,
        )

    if fam_value == PolymerFamily.ALGINATE_CHITOSAN.value:
        from .tier2_families import solve_alginate_chitosan_pec_gelation
        return solve_alginate_chitosan_pec_gelation(
            params=params, props=props, R_droplet=R_droplet,
            mode=mode, timing=timing,
        )

    if fam_value == PolymerFamily.CHITIN.value:
        # CHITIN material-as-ligand: structurally analogous to amylose
        # (β-1,4 vs α-1,4 glucan; both -OH-rich); delegate to the same
        # dextran-ECH analogy and re-tag.
        from dataclasses import replace as _dc_replace

        from .dextran_ech import solve_dextran_ech_gelation
        sandbox = _dc_replace(props, polymer_family=PolymerFamily.DEXTRAN)
        result = solve_dextran_ech_gelation(
            params=params, props=sandbox, R_droplet=R_droplet,
            mode=mode, timing=timing,
        )
        new_manifest = _dc_replace(
            result.model_manifest,
            model_name="L2.chitin_cbd.semi_quantitative_v9_3",
            assumptions=list(result.model_manifest.assumptions) + [
                "CHITIN bead L2 gelation modeled by analogy to "
                "Sephadex-class crosslinked dextran (analogous "
                "polysaccharide chemistry). Material-as-ligand (B9) "
                "pattern: chitin matrix IS the affinity ligand for "
                "CBD-tagged fusions (NEB IMPACT system).",
            ],
        )
        return _dc_replace(
            result,
            model_tier="chitin_cbd_via_dextran_v9_3",
            model_manifest=new_manifest,
        )

    # ── v9.4 Tier-3 promoted families ────────────────────────────────
    if fam_value == PolymerFamily.PECTIN.value:
        from .tier3_families import solve_pectin_gelation
        return solve_pectin_gelation(
            params=params, props=props, R_droplet=R_droplet,
            mode=mode, timing=timing,
        )

    if fam_value == PolymerFamily.GELLAN.value:
        from .tier3_families import solve_gellan_gelation
        return solve_gellan_gelation(
            params=params, props=props, R_droplet=R_droplet,
            mode=mode, timing=timing,
        )

    if fam_value == PolymerFamily.PULLULAN.value:
        from .tier3_families import solve_pullulan_gelation
        return solve_pullulan_gelation(
            params=params, props=props, R_droplet=R_droplet,
            mode=mode, timing=timing,
        )

    if fam_value == PolymerFamily.STARCH.value:
        from .tier3_families import solve_starch_gelation
        return solve_starch_gelation(
            params=params, props=props, R_droplet=R_droplet,
            mode=mode, timing=timing,
        )

    # ── v9.5 Tier-3 multi-variant composite promotions ────────────────
    # Promoted from v9.4 data-only placeholders. Each delegates to the
    # closest single-component solver (alginate ionic-Ca for the
    # PEC/co-gelation paths, dextran-ECH for the neutral-glucan path)
    # and re-tags with composite provenance per the v9_5_composites
    # module's _retag_composite helper.
    if fam_value == PolymerFamily.PECTIN_CHITOSAN.value:
        from .v9_5_composites import solve_pectin_chitosan_pec_gelation
        return solve_pectin_chitosan_pec_gelation(
            params=params, props=props, R_droplet=R_droplet,
            mode=mode, timing=timing,
        )

    if fam_value == PolymerFamily.GELLAN_ALGINATE.value:
        from .v9_5_composites import solve_gellan_alginate_gelation
        return solve_gellan_alginate_gelation(
            params=params, props=props, R_droplet=R_droplet,
            mode=mode, timing=timing,
        )

    if fam_value == PolymerFamily.PULLULAN_DEXTRAN.value:
        from .v9_5_composites import solve_pullulan_dextran_gelation
        return solve_pullulan_dextran_gelation(
            params=params, props=props, R_droplet=R_droplet,
            mode=mode, timing=timing,
        )

    raise ValueError(
        f"Unknown polymer_family.value = {fam_value!r}. "
        f"Known UI-enabled families: AGAROSE_CHITOSAN, AGAROSE, CHITOSAN, "
        f"DEXTRAN, AMYLOSE, HYALURONATE, KAPPA_CARRAGEENAN, AGAROSE_DEXTRAN, "
        f"AGAROSE_ALGINATE, ALGINATE_CHITOSAN, CHITIN, PECTIN, GELLAN, "
        f"PULLULAN, STARCH, PECTIN_CHITOSAN, GELLAN_ALGINATE, "
        f"PULLULAN_DEXTRAN, plus pipeline-branch families ALGINATE/"
        f"CELLULOSE/PLGA."
    )


__all__ = ["solve_gelation_by_family"]
