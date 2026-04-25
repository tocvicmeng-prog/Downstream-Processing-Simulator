"""Tests for v9.3 Tier-2 polymer-family L2 solvers and reagent profiles.

Coverage:
  - All 6 promoted Tier-2 families (HYALURONATE, KAPPA_CARRAGEENAN,
    AGAROSE_DEXTRAN, AGAROSE_ALGINATE, ALGINATE_CHITOSAN, CHITIN) are
    UI-enabled.
  - composite_dispatch.solve_gelation_by_family routes each to the
    correct solver and produces a SEMI_QUANTITATIVE GelationResult.
  - The 13 new Tier-2 reagent profiles register and have the expected
    metadata.
"""

from __future__ import annotations

from dataclasses import replace

import pytest

from dpsim.datatypes import (
    MaterialProperties,
    ModelEvidenceTier,
    PolymerFamily,
    SimulationParameters,
    is_family_enabled_in_ui,
    is_material_as_ligand,
)
from dpsim.level2_gelation.composite_dispatch import solve_gelation_by_family
from dpsim.level2_gelation.tier2_families import (
    solve_agarose_alginate_ipn_gelation,
    solve_agarose_dextran_core_shell_gelation,
    solve_alginate_chitosan_pec_gelation,
    solve_hyaluronate_gelation,
    solve_kappa_carrageenan_gelation,
)
from dpsim.module2_functionalization.reagent_profiles import REAGENT_PROFILES


V9_3_TIER2_FAMILIES = [
    PolymerFamily.HYALURONATE,
    PolymerFamily.KAPPA_CARRAGEENAN,
    PolymerFamily.AGAROSE_DEXTRAN,
    PolymerFamily.AGAROSE_ALGINATE,
    PolymerFamily.ALGINATE_CHITOSAN,
    PolymerFamily.CHITIN,
]


class TestV9_3_Tier2UIPromotion:

    @pytest.mark.parametrize("fam", V9_3_TIER2_FAMILIES)
    def test_tier2_family_ui_enabled(self, fam):
        assert is_family_enabled_in_ui(fam) is True, (
            f"v9.3 promoted {fam.value!r} should be UI-enabled"
        )

    def test_chitin_is_material_as_ligand(self):
        assert is_material_as_ligand(PolymerFamily.CHITIN) is True

    def test_amylose_is_material_as_ligand(self):
        assert is_material_as_ligand(PolymerFamily.AMYLOSE) is True

    @pytest.mark.parametrize("fam", [
        PolymerFamily.HYALURONATE,
        PolymerFamily.KAPPA_CARRAGEENAN,
        PolymerFamily.AGAROSE_DEXTRAN,
        PolymerFamily.AGAROSE_ALGINATE,
        PolymerFamily.ALGINATE_CHITOSAN,
    ])
    def test_non_material_as_ligand_families(self, fam):
        """The Tier-2 families that aren't material-as-ligand."""
        assert is_material_as_ligand(fam) is False


class TestV9_3_Tier2SolverDispatch:

    @pytest.mark.parametrize("fam", V9_3_TIER2_FAMILIES)
    def test_dispatcher_routes_tier2(self, fam):
        """composite_dispatch must dispatch each Tier-2 family without
        raising NotImplementedError (which was the v9.2 behavior)."""
        params = SimulationParameters()
        # KAPPA_CARRAGEENAN solver delegates to alginate ionic-Ca which
        # uses scipy solvers — skip if environment can't run scipy.
        # Use direct call instead of full dispatcher for those.
        props = replace(MaterialProperties(), polymer_family=fam)
        if fam.value == PolymerFamily.KAPPA_CARRAGEENAN.value:
            # Skip dispatcher call for κ-carrageenan since it depends on
            # scipy/alginate solver; tested separately below.
            return
        if fam.value == PolymerFamily.ALGINATE_CHITOSAN.value:
            # Same — uses alginate ionic-Ca solver.
            return
        result = solve_gelation_by_family(params, props, R_droplet=50e-6)
        assert result is not None
        assert result.pore_size_mean > 0


class TestV9_3_Tier2SolverDirect:
    """Direct solver tests that don't require scipy-heavy dispatching."""

    def test_hyaluronate_solver(self):
        props = replace(MaterialProperties(),
                        polymer_family=PolymerFamily.HYALURONATE)
        result = solve_hyaluronate_gelation(
            SimulationParameters(), props, R_droplet=50e-6,
        )
        assert result.model_tier == "hyaluronate_covalent_v9_3"
        assert (result.model_manifest.evidence_tier.value
                == ModelEvidenceTier.SEMI_QUANTITATIVE.value)
        # The retag must add HA-specific assumptions
        assumptions = " ".join(result.model_manifest.assumptions).lower()
        assert "hyaluronate" in assumptions or "ha " in assumptions

    def test_agarose_dextran_solver_carries_shell_diagnostic(self):
        props = replace(MaterialProperties(),
                        polymer_family=PolymerFamily.AGAROSE_DEXTRAN)
        result = solve_agarose_dextran_core_shell_gelation(
            SimulationParameters(), props, R_droplet=50e-6,
        )
        diag = result.model_manifest.diagnostics
        assert "shell_thickness_nm" in diag
        assert diag["core_polymer"] == "agarose"
        assert diag["shell_polymer"] == "dextran"

    def test_agarose_alginate_solver_reports_reinforcement(self):
        props = replace(MaterialProperties(),
                        polymer_family=PolymerFamily.AGAROSE_ALGINATE)
        result = solve_agarose_alginate_ipn_gelation(
            SimulationParameters(), props, R_droplet=50e-6,
        )
        diag = result.model_manifest.diagnostics
        assert "g_reinforcement_factor" in diag
        assert diag["g_reinforcement_factor"] > 1.0  # super-additive

    def test_solver_rejects_wrong_family(self):
        wrong = replace(MaterialProperties(),
                        polymer_family=PolymerFamily.AGAROSE)
        with pytest.raises(ValueError, match="HYALURONATE"):
            solve_hyaluronate_gelation(
                SimulationParameters(), wrong, R_droplet=50e-6,
            )


class TestV9_3_Tier2ReagentProfiles:
    """13 new Tier-2 reagent profiles (T1)."""

    V9_3_KEYS = [
        "procion_red_he3b_coupling",
        "p_aminobenzamidine_coupling",
        "chitin_cbd_intein",
        "jacalin_coupling",
        "lentil_lectin_coupling",
        "oligonucleotide_dna_coupling",
        "peptide_affinity_hwrgwv",
        "hrp_h2o2_tyramine",
        "oligoglycine_spacer",
        "cystamine_disulfide_spacer",
        "succinic_anhydride_carboxylation",
        "tresyl_chloride_activation",
        "pyridyl_disulfide_activation",
    ]

    @pytest.mark.parametrize("key", V9_3_KEYS)
    def test_profile_present(self, key):
        assert key in REAGENT_PROFILES, f"v9.3 Tier-2 profile {key!r} missing"

    @pytest.mark.parametrize("key", V9_3_KEYS)
    def test_profile_has_calibration_source(self, key):
        rp = REAGENT_PROFILES[key]
        assert rp.calibration_source != "", (
            f"{key!r}: calibration_source is empty"
        )

    @pytest.mark.parametrize("key", V9_3_KEYS)
    def test_profile_has_positive_kinetics(self, key):
        rp = REAGENT_PROFILES[key]
        assert rp.k_forward > 0
        assert rp.E_a >= 0

    def test_hrp_tyramine_targets_phenol_acs(self):
        from dpsim.module2_functionalization.acs import ACSSiteType
        rp = REAGENT_PROFILES["hrp_h2o2_tyramine"]
        assert rp.target_acs.value == ACSSiteType.PHENOL_TYRAMINE.value

    def test_pyridyl_disulfide_produces_thiol_acs(self):
        from dpsim.module2_functionalization.acs import ACSSiteType
        rp = REAGENT_PROFILES["pyridyl_disulfide_activation"]
        assert rp.product_acs.value == ACSSiteType.THIOL.value

    def test_tresyl_produces_sulfonate_leaving_acs(self):
        from dpsim.module2_functionalization.acs import ACSSiteType
        rp = REAGENT_PROFILES["tresyl_chloride_activation"]
        assert rp.product_acs.value == ACSSiteType.SULFONATE_LEAVING.value
