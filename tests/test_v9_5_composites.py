"""v9.5 Tier-3 multi-variant composite acceptance tests.

Covers the three composite families promoted from v9.4 data-only
placeholder status:

  - PECTIN_CHITOSAN  (PEC shell, mirror of v9.3 ALGINATE_CHITOSAN PEC)
  - GELLAN_ALGINATE  (dual ionic-gel composite)
  - PULLULAN_DEXTRAN (neutral α-glucan composite)

The three solvers follow the parallel-module + delegate-and-retag
pattern (D-016/D-017/D-027/D-037). Each:

* enforces ``polymer_family.value`` via ``.value`` comparison (per the
  CLAUDE.md AST-enforced rule)
* delegates to a single-component solver in a sandbox where the family
  is temporarily set to the delegate's expected value
* re-tags the result with ``L2.<family>.qualitative_trend_v9_5``
  model_name and a ``v9.5_tier_3_composite`` diagnostic tag
* defaults to ``QUALITATIVE_TREND`` evidence

Test layout mirrors ``test_v9_4_tier3.py``: UI-promotion gates,
direct-call solver tests (no scipy delegate path where possible),
dispatcher routing, and a borax-reversibility-warning surface check.
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
)
from dpsim.level2_gelation.composite_dispatch import solve_gelation_by_family
from dpsim.level2_gelation.v9_5_composites import (
    solve_gellan_alginate_gelation,
    solve_pectin_chitosan_pec_gelation,
    solve_pullulan_dextran_gelation,
)


V9_5_COMPOSITE_FAMILIES = [
    PolymerFamily.PECTIN_CHITOSAN,
    PolymerFamily.GELLAN_ALGINATE,
    PolymerFamily.PULLULAN_DEXTRAN,
]


# --------------------------------------------------------------------------- #
# 1) UI promotion                                                              #
# --------------------------------------------------------------------------- #


class TestV9_5_UIPromotion:
    @pytest.mark.parametrize("fam", V9_5_COMPOSITE_FAMILIES)
    def test_composite_family_ui_enabled(self, fam: PolymerFamily) -> None:
        assert is_family_enabled_in_ui(fam) is True, (
            f"v9.5 Tier-3 composite {fam.value!r} should be UI-enabled "
            f"after v9.5 promotion"
        )

    def test_v9_5_promotions_appear_in_family_selector_display(self) -> None:
        """Selector display rows must include all three composites."""
        from dpsim.visualization.tabs.m1.family_selector import (
            _FAMILY_DISPLAY,
        )

        present = {fam.value for _, fam, _ in _FAMILY_DISPLAY}
        for fam in V9_5_COMPOSITE_FAMILIES:
            assert fam.value in present, (
                f"{fam.value!r} missing from family-selector display rows"
            )

    def test_borax_reversibility_warning_in_preview(self) -> None:
        """The borax row in _TIER2_PREVIEW_ROWS must surface the
        REVERSIBILITY WARNING tag and the temporary-porogen guidance."""
        from dpsim.visualization.tabs.m1.family_selector import (
            _TIER2_PREVIEW_ROWS,
        )

        borax_rows = [
            (name, body) for name, body in _TIER2_PREVIEW_ROWS
            if "borax" in name.lower() or "borate" in name.lower()
        ]
        assert len(borax_rows) == 1
        name, body = borax_rows[0]
        assert "REVERSIBILITY WARNING" in name
        assert "TEMPORARY POROGEN" in body
        assert "BDDE" in body or "ECH" in body

    def test_v9_5_preview_no_longer_lists_promoted_composites(self) -> None:
        """The preview list must no longer carry the three v9.5
        promoted families (they're selectable in the radio above)."""
        from dpsim.visualization.tabs.m1.family_selector import (
            _TIER2_PREVIEW_ROWS,
        )

        preview_text = " ".join(name for name, _ in _TIER2_PREVIEW_ROWS).lower()
        assert "pectin-chitosan" not in preview_text
        assert "gellan-alginate" not in preview_text
        assert "pullulan-dextran" not in preview_text


# --------------------------------------------------------------------------- #
# 2) Direct solver tests                                                       #
# --------------------------------------------------------------------------- #


class TestV9_5_SolverDirect:
    """Direct-call solver tests that exercise the delegate-and-retag pattern."""

    def test_pullulan_dextran_solver(self) -> None:
        """Pullulan-dextran routes through dextran-ECH (no scipy)."""
        props = replace(
            MaterialProperties(), polymer_family=PolymerFamily.PULLULAN_DEXTRAN,
        )
        result = solve_pullulan_dextran_gelation(
            SimulationParameters(), props, R_droplet=50e-6,
        )
        assert result.model_tier == "pullulan_dextran_v9_5"
        assert result.pore_size_mean > 0
        manifest = result.model_manifest
        assert manifest.evidence_tier.value == ModelEvidenceTier.QUALITATIVE_TREND.value
        assert manifest.diagnostics["polymer_family"] == PolymerFamily.PULLULAN_DEXTRAN.value
        assert manifest.diagnostics["tier"] == "v9.5_tier_3_composite"
        assert manifest.diagnostics["constituents"] == "pullulan + dextran"
        # SA screening § 6.4 bioprocess-relevance note must be in assumptions
        assert any("Drug-delivery applications dominate" in a
                   for a in manifest.assumptions)

    def test_pullulan_dextran_solver_rejects_wrong_family(self) -> None:
        wrong = replace(
            MaterialProperties(), polymer_family=PolymerFamily.AGAROSE,
        )
        with pytest.raises(ValueError, match="PULLULAN_DEXTRAN"):
            solve_pullulan_dextran_gelation(
                SimulationParameters(), wrong, R_droplet=50e-6,
            )

    def test_pectin_chitosan_solver_rejects_wrong_family(self) -> None:
        wrong = replace(
            MaterialProperties(), polymer_family=PolymerFamily.ALGINATE_CHITOSAN,
        )
        with pytest.raises(ValueError, match="PECTIN_CHITOSAN"):
            solve_pectin_chitosan_pec_gelation(
                SimulationParameters(), wrong, R_droplet=50e-6,
            )

    def test_gellan_alginate_solver_rejects_wrong_family(self) -> None:
        wrong = replace(
            MaterialProperties(), polymer_family=PolymerFamily.GELLAN,
        )
        with pytest.raises(ValueError, match="GELLAN_ALGINATE"):
            solve_gellan_alginate_gelation(
                SimulationParameters(), wrong, R_droplet=50e-6,
            )

    def test_solvers_reject_non_empirical_mode(self) -> None:
        """All three v9.5 solvers support 'empirical' only at v9.5 launch."""
        props = replace(
            MaterialProperties(), polymer_family=PolymerFamily.PULLULAN_DEXTRAN,
        )
        with pytest.raises(NotImplementedError, match="empirical"):
            solve_pullulan_dextran_gelation(
                SimulationParameters(), props, R_droplet=50e-6,
                mode="mechanistic",
            )


# --------------------------------------------------------------------------- #
# 3) Dispatcher routing                                                        #
# --------------------------------------------------------------------------- #


class TestV9_5_Dispatch:
    def test_dispatcher_routes_pullulan_dextran(self) -> None:
        """PULLULAN_DEXTRAN goes through dextran-ECH delegate (no scipy)."""
        props = replace(
            MaterialProperties(), polymer_family=PolymerFamily.PULLULAN_DEXTRAN,
        )
        result = solve_gelation_by_family(
            SimulationParameters(), props, R_droplet=50e-6,
        )
        assert result.model_tier == "pullulan_dextran_v9_5"
        assert result.pore_size_mean > 0

    def test_dispatcher_routes_pectin_chitosan_to_v9_5_solver(self) -> None:
        """Mock-style routing test that doesn't invoke the heavy
        scipy-BDF alginate-ionic-Ca path. We monkey-patch the v9.5
        solver and confirm it gets called."""
        import dpsim.level2_gelation.v9_5_composites as v9_5_mod

        called: dict[str, bool] = {}
        original = v9_5_mod.solve_pectin_chitosan_pec_gelation

        def stub(*args, **kwargs):
            called["pectin_chitosan"] = True
            raise StopIteration("routing-test sentinel")

        v9_5_mod.solve_pectin_chitosan_pec_gelation = stub
        try:
            props = replace(
                MaterialProperties(),
                polymer_family=PolymerFamily.PECTIN_CHITOSAN,
            )
            with pytest.raises(StopIteration, match="routing-test sentinel"):
                solve_gelation_by_family(
                    SimulationParameters(), props, R_droplet=50e-6,
                )
        finally:
            v9_5_mod.solve_pectin_chitosan_pec_gelation = original
        assert called.get("pectin_chitosan") is True

    def test_dispatcher_routes_gellan_alginate_to_v9_5_solver(self) -> None:
        """Same mock-style approach for GELLAN_ALGINATE dispatch."""
        import dpsim.level2_gelation.v9_5_composites as v9_5_mod

        called: dict[str, bool] = {}
        original = v9_5_mod.solve_gellan_alginate_gelation

        def stub(*args, **kwargs):
            called["gellan_alginate"] = True
            raise StopIteration("routing-test sentinel")

        v9_5_mod.solve_gellan_alginate_gelation = stub
        try:
            props = replace(
                MaterialProperties(),
                polymer_family=PolymerFamily.GELLAN_ALGINATE,
            )
            with pytest.raises(StopIteration, match="routing-test sentinel"):
                solve_gelation_by_family(
                    SimulationParameters(), props, R_droplet=50e-6,
                )
        finally:
            v9_5_mod.solve_gellan_alginate_gelation = original
        assert called.get("gellan_alginate") is True

    def test_dispatcher_does_not_raise_v9_4_placeholder_error(self) -> None:
        """Smoke: the legacy v9.4 NotImplementedError 'placeholder' gate
        must be gone. PULLULAN_DEXTRAN (no scipy) is the safest probe."""
        props = replace(
            MaterialProperties(),
            polymer_family=PolymerFamily.PULLULAN_DEXTRAN,
        )
        # If the v9.4 placeholder gate were still in place, this would
        # raise NotImplementedError with "placeholder" in the message.
        result = solve_gelation_by_family(
            SimulationParameters(), props, R_droplet=50e-6,
        )
        assert result is not None


# --------------------------------------------------------------------------- #
# 4) Composite manifest discipline                                             #
# --------------------------------------------------------------------------- #


class TestV9_5_ManifestDiscipline:
    def test_pullulan_dextran_manifest_calibration_ref_set(self) -> None:
        props = replace(
            MaterialProperties(), polymer_family=PolymerFamily.PULLULAN_DEXTRAN,
        )
        result = solve_pullulan_dextran_gelation(
            SimulationParameters(), props, R_droplet=50e-6,
        )
        cref = result.model_manifest.calibration_ref
        # Composite calibration_ref should not be empty; exact value
        # is the literature anchor.
        assert cref != ""
        assert "singh_2008" in cref or "carbohydr" in cref.lower() or "macromol" in cref.lower()

    def test_pullulan_dextran_assumption_list_carries_sa_screening_note(self) -> None:
        props = replace(
            MaterialProperties(), polymer_family=PolymerFamily.PULLULAN_DEXTRAN,
        )
        result = solve_pullulan_dextran_gelation(
            SimulationParameters(), props, R_droplet=50e-6,
        )
        text = "\n".join(result.model_manifest.assumptions)
        # SA screening § 6.4 attribution
        assert "SA screening" in text
        assert "QUALITATIVE_TREND" in text
        # Constituent-only-calibration warning
        assert "neutral α-glucans" in text or "α-glucan" in text


# --------------------------------------------------------------------------- #
# 5) Enum-comparison enforcement (CLAUDE.md AST gate)                          #
# --------------------------------------------------------------------------- #


def test_v9_5_composites_module_passes_enum_comparison_ast_gate() -> None:
    """The v9_5_composites module must pass the AST gate that forbids
    ``is`` / ``is not`` comparisons against PolymerFamily, ACSSiteType,
    ModelEvidenceTier, ModelMode (per CLAUDE.md and
    test_v9_3_enum_comparison_enforcement.py)."""
    import ast
    from pathlib import Path

    src = Path(
        "src/dpsim/level2_gelation/v9_5_composites.py"
    ).read_text(encoding="utf-8")
    tree = ast.parse(src)

    BANNED = {"PolymerFamily", "ACSSiteType", "ModelEvidenceTier", "ModelMode"}

    for node in ast.walk(tree):
        if isinstance(node, ast.Compare):
            for op, comparator in zip(node.ops, node.comparators):
                if isinstance(op, (ast.Is, ast.IsNot)):
                    target = comparator
                    if isinstance(target, ast.Attribute):
                        # X.Y -> get X (e.g. PolymerFamily.PECTIN -> PolymerFamily)
                        if isinstance(target.value, ast.Name):
                            assert target.value.id not in BANNED, (
                                f"v9_5_composites.py uses 'is'/'is not' against "
                                f"{target.value.id} at line {node.lineno}; "
                                f"use .value comparison per CLAUDE.md"
                            )
