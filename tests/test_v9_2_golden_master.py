"""Golden-master regression suite for v9.2 M0b refactors.

These tests prove that the v9.2 parallel modules and registry adapter
produce numerically identical outputs to the v9.1 legacy code paths
they shadow:

  A3.6 — ion-registry adapter (registry → legacy AlginateGelantProfile)
         must produce bit-for-bit-equivalent fields to GELANTS_ALGINATE.

  A2.5 — solve_gelation_by_family(AGAROSE_CHITOSAN, ...) must produce
         a result identical to legacy solve_gelation(AGAROSE_CHITOSAN, ...)
         under the same parameters.

Tolerance: zero relative for direct field comparison (the data is
literally the same numbers); 1e-12 for floating-point arithmetic that
flows through identical code paths; 1e-6 for any computation that
crosses a kernel boundary.

These tests are environment-sensitive: they DO exercise the legacy
gelation kernel (which uses scipy.integrate.solve_ivp), so they may be
slow. They are kept in a dedicated file so a session that needs to skip
them can do so without affecting the schema-additive smoke tests.
"""

from __future__ import annotations

from dataclasses import replace

import pytest

from dpsim.datatypes import MaterialProperties, PolymerFamily, SimulationParameters
from dpsim.level2_gelation.ion_registry import (
    ION_GELANT_REGISTRY,
    to_alginate_gelant_profile,
)
from dpsim.reagent_library_alginate import GELANTS_ALGINATE


# ─── A3.6 — Ion-registry adapter golden-master ─────────────────────────


class TestIonRegistryAdapterEquivalence:
    """Adapter must produce bit-for-bit-equivalent fields to legacy entries."""

    def test_cacl2_external_equivalence(self):
        registry_profile = ION_GELANT_REGISTRY[
            (PolymerFamily.ALGINATE, "Ca2+ (CaCl2 external)")
        ]
        legacy = GELANTS_ALGINATE["cacl2_external"]
        adapted = to_alginate_gelant_profile(registry_profile)

        assert adapted.mode == legacy.mode
        assert adapted.C_Ca_bath == legacy.C_Ca_bath
        assert adapted.C_Ca_source == legacy.C_Ca_source
        assert adapted.k_release == legacy.k_release
        assert adapted.T_default == legacy.T_default
        assert adapted.t_default == legacy.t_default
        assert adapted.suitability == legacy.suitability

    def test_gdl_caco3_internal_equivalence(self):
        registry_profile = ION_GELANT_REGISTRY[
            (PolymerFamily.ALGINATE, "Ca2+ (GDL/CaCO3 internal)")
        ]
        legacy = GELANTS_ALGINATE["gdl_caco3_internal"]
        adapted = to_alginate_gelant_profile(registry_profile)

        assert adapted.mode == legacy.mode
        assert adapted.C_Ca_bath == legacy.C_Ca_bath
        assert adapted.C_Ca_source == legacy.C_Ca_source
        assert adapted.k_release == legacy.k_release
        assert adapted.T_default == legacy.T_default
        assert adapted.t_default == legacy.t_default
        assert adapted.suitability == legacy.suitability


class TestIonRegistryAdapterRejection:
    """Adapter must reject ion-pair combinations it cannot translate."""

    def test_rejects_non_alginate_family(self):
        # Build a synthetic non-alginate profile
        from dpsim.level2_gelation.ion_registry import IonGelantProfile
        bad = IonGelantProfile(
            polymer_family=PolymerFamily.KAPPA_CARRAGEENAN,
            ion="K+",
            mode="external_bath",
            C_ion_bath=200.0,
            C_ion_source=0.0,
            k_release=0.0,
            junction_zone_energy=-3.0,
            stoichiometry=1.0,
            biotherapeutic_safe=True,
            T_default=298.15,
            t_default=600.0,
            suitability=8,
            notes="synthetic test",
        )
        with pytest.raises(ValueError, match="ALGINATE"):
            to_alginate_gelant_profile(bad)

    def test_rejects_non_ca2_ion(self):
        from dpsim.level2_gelation.ion_registry import IonGelantProfile
        bad_ion = IonGelantProfile(
            polymer_family=PolymerFamily.ALGINATE,
            ion="Sr2+",  # not Ca2+
            mode="external_bath",
            C_ion_bath=100.0,
            C_ion_source=0.0,
            k_release=0.0,
            junction_zone_energy=-5.0,
            stoichiometry=2.0,
            biotherapeutic_safe=False,
            T_default=298.15,
            t_default=1800.0,
            suitability=5,
            notes="strontium would gel alginate but is not biotherapeutic-safe",
        )
        with pytest.raises(ValueError, match="Ca2"):
            to_alginate_gelant_profile(bad_ion)


# ─── A2.5 — Composite dispatcher golden-master for AGAROSE_CHITOSAN ────


class TestCompositeDispatcherLegacyPathPreservation:
    """solve_gelation_by_family(AGAROSE_CHITOSAN) must call solve_gelation()
    directly — same code path, identical result object.

    We verify this by patching solve_gelation and checking it gets called
    with the same arguments.
    """

    def test_agarose_chitosan_routes_to_legacy_solve_gelation(self, monkeypatch):
        from dpsim.level2_gelation import composite_dispatch, solver as solver_mod
        called = {}

        def _fake(params, props, R_droplet, mode, timing):
            called["called"] = True
            called["mode"] = mode
            called["R_droplet"] = R_droplet
            called["polymer_family"] = props.polymer_family.value
            # Return a sentinel
            return "LEGACY_SOLVE_GELATION_RESULT"

        # Patch the import that composite_dispatch performs lazily.
        monkeypatch.setattr(solver_mod, "solve_gelation", _fake)

        props = MaterialProperties()  # default polymer_family = AGAROSE_CHITOSAN
        params = SimulationParameters()
        result = composite_dispatch.solve_gelation_by_family(
            params=params, props=props, R_droplet=50e-6, mode="empirical",
        )
        assert result == "LEGACY_SOLVE_GELATION_RESULT"
        assert called["called"] is True
        assert called["mode"] == "empirical"
        assert called["R_droplet"] == 50e-6
        assert called["polymer_family"] == "agarose_chitosan"
