"""Tests for B2 — family-aware trust gate.

Reference: docs/dev_orchestrator_plan.md, Module B2.

The legacy trust gate fired several warnings (NH2 ratio, agarose calibration
range, chitosan-NH2 hydroxyl side reactions, IPN eta_coupling) that only
make sense for the agarose+chitosan platform. v0.3.0 gates these on
``props.polymer_family == AGAROSE_CHITOSAN`` and emits a single advisory
warning for non-A+C families until per-family trust gates land in v0.4.0+.
"""

from __future__ import annotations

from dataclasses import replace

import pytest

from dpsim.datatypes import (
    PolymerFamily,
)
from dpsim.properties.database import PropertyDatabase
from dpsim.trust import assess_trust


@pytest.fixture
def fast_smoke_run():
    """Run the smoke simulation once and return (result, params, props)."""
    from pathlib import Path

    from dpsim.config import load_config
    from dpsim.pipeline.orchestrator import PipelineOrchestrator

    params = load_config(Path("configs/fast_smoke.toml"))
    db = PropertyDatabase()
    orch = PipelineOrchestrator(db=db)
    result = orch.run_single(params)
    props = db.update_for_conditions(
        T_oil=params.formulation.T_oil,
        c_agarose=params.formulation.c_agarose,
        c_chitosan=params.formulation.c_chitosan,
        c_span80=params.formulation.c_span80,
    )
    return result, params, props


class TestFamilyAwareTrust:
    def test_agarose_chitosan_default_no_advisory(self, fast_smoke_run):
        """A+C is the default; no family-level advisory should fire."""
        result, params, props = fast_smoke_run
        assert props.polymer_family == PolymerFamily.AGAROSE_CHITOSAN
        trust = assess_trust(result, params, props)
        advisory = [
            w for w in trust.warnings if "calibrated primarily" in w
        ]
        assert advisory == []

    def test_alginate_emits_advisory(self, fast_smoke_run):
        """Non-A+C family triggers the calibration-scope advisory."""
        result, params, props = fast_smoke_run
        props_alg = replace(props, polymer_family=PolymerFamily.ALGINATE)
        trust = assess_trust(result, params, props_alg)
        advisory = [w for w in trust.warnings if "calibrated primarily" in w]
        assert len(advisory) == 1
        assert "alginate" in advisory[0]

    def test_alginate_skips_ac_specific_checks(self, fast_smoke_run):
        """Alginate runs do NOT receive A+C-specific NH2/agarose-pct warnings."""
        result, params, props = fast_smoke_run
        # Force a c_genipin/NH2 ratio that would otherwise trip the A+C check.
        params_low_x = replace(
            params,
            formulation=replace(
                params.formulation,
                c_genipin=0.001,  # extremely low to trigger NH2 ratio warning
            ),
        )
        props_alg = replace(props, polymer_family=PolymerFamily.ALGINATE)
        trust = assess_trust(result, params_low_x, props_alg)
        nh2_warnings = [w for w in trust.warnings if "Crosslinker/NH2 ratio" in w]
        assert nh2_warnings == [], (
            f"alginate runs should not see A+C NH2-ratio warnings; got {nh2_warnings}"
        )
        agarose_warnings = [w for w in trust.warnings if "empirical pore model" in w]
        assert agarose_warnings == [], (
            f"alginate runs should not see A+C agarose-calibration warnings; got {agarose_warnings}"
        )

    def test_cellulose_skips_ac_specific_checks(self, fast_smoke_run):
        result, params, props = fast_smoke_run
        props_cel = replace(props, polymer_family=PolymerFamily.CELLULOSE)
        trust = assess_trust(result, params, props_cel)
        ac_specific = [
            w for w in trust.warnings
            if "Crosslinker/NH2 ratio" in w
            or "empirical pore model" in w
            or "IPN coupling coefficient" in w
            or "Hydroxyl crosslinker model" in w
        ]
        assert ac_specific == [], (
            f"cellulose should not see A+C-specific warnings; got {ac_specific}"
        )

    def test_plga_advisory(self, fast_smoke_run):
        result, params, props = fast_smoke_run
        props_plga = replace(props, polymer_family=PolymerFamily.PLGA)
        trust = assess_trust(result, params, props_plga)
        assert any("calibrated primarily" in w for w in trust.warnings)
        assert any("plga" in w.lower() for w in trust.warnings)
