"""Tests for C4 — ResultGraph.register_result helper + M2 sub-step provenance.

Reference: docs/handover/V0_3_0_FAMILY_COVERAGE_HANDOVER.md §10 (v0.4.0 C4).
Closes architect-coherence-audit D3 ResultGraph finding for the M2 stage.
"""

from __future__ import annotations

from dataclasses import dataclass


from dpsim.core.result_graph import ResultGraph, ResultNode
from dpsim.datatypes import ModelEvidenceTier, ModelManifest


@dataclass
class _MockResult:
    """Minimal typed result with a ``model_manifest`` attribute."""

    model_manifest: ModelManifest | None = None


def _semi_manifest(name: str = "M2.test") -> ModelManifest:
    return ModelManifest(
        model_name=name,
        evidence_tier=ModelEvidenceTier.SEMI_QUANTITATIVE,
    )


# ─── register_result helper ──────────────────────────────────────────────────


class TestRegisterResult:
    def test_creates_node(self):
        graph = ResultGraph()
        result = _MockResult(model_manifest=_semi_manifest())
        node = graph.register_result(
            result, node_id="step_1", stage="M2", label="ECH activation"
        )
        assert isinstance(node, ResultNode)
        assert node.node_id == "step_1"
        assert node.stage == "M2"
        assert node.label == "ECH activation"
        assert node.payload is result
        assert node.manifest is result.model_manifest

    def test_no_manifest_still_registers(self):
        graph = ResultGraph()
        result = _MockResult(model_manifest=None)
        node = graph.register_result(result, node_id="x", stage="M2", label="x")
        assert node.manifest is None
        assert "x" in graph.nodes

    def test_depends_on_creates_edges(self):
        graph = ResultGraph()
        graph.register_result(
            _MockResult(model_manifest=_semi_manifest("step_1")),
            node_id="step_1", stage="M2", label="step 1",
        )
        graph.register_result(
            _MockResult(model_manifest=_semi_manifest("step_2")),
            node_id="step_2", stage="M2", label="step 2",
            depends_on=["step_1"], relation="follows",
        )
        edges = [(e.source, e.target, e.relation) for e in graph.edges]
        assert ("step_1", "step_2", "follows") in edges

    def test_diagnostics_and_caveats_passed_through(self):
        graph = ResultGraph()
        node = graph.register_result(
            _MockResult(model_manifest=_semi_manifest()),
            node_id="x", stage="M2", label="x",
            diagnostics={"k": 1.0},
            wet_lab_caveats=["test caveat"],
        )
        assert node.diagnostics == {"k": 1.0}
        assert node.wet_lab_caveats == ["test caveat"]

    def test_weakest_tier_includes_registered_results(self):
        graph = ResultGraph()
        graph.register_result(
            _MockResult(
                model_manifest=ModelManifest(
                    model_name="strong",
                    evidence_tier=ModelEvidenceTier.CALIBRATED_LOCAL,
                )
            ),
            node_id="strong_node", stage="M2", label="strong",
        )
        graph.register_result(
            _MockResult(
                model_manifest=ModelManifest(
                    model_name="weak",
                    evidence_tier=ModelEvidenceTier.QUALITATIVE_TREND,
                )
            ),
            node_id="weak_node", stage="M2", label="weak",
        )
        # weakest_evidence_tier returns the WEAKEST = QUALITATIVE_TREND
        assert graph.weakest_evidence_tier() == ModelEvidenceTier.QUALITATIVE_TREND


# ─── M2 sub-step graph integration ───────────────────────────────────────────


class TestM2SubStepGraph:
    """ModificationOrchestrator registers per-step nodes when graph is supplied."""

    def test_modification_orchestrator_registers_substeps(self):
        from dpsim.lifecycle.orchestrator import (
            default_protein_a_functionalization_steps,
        )
        from dpsim.module2_functionalization.orchestrator import (
            ModificationOrchestrator,
        )
        from dpsim.pipeline.orchestrator import export_for_module2
        from dpsim.properties.database import PropertyDatabase
        from dpsim.lifecycle import run_m1_from_recipe
        from dpsim.core.process_recipe import default_affinity_media_recipe
        from dpsim.trust import assess_trust

        # Run M1 to get a contract
        recipe = default_affinity_media_recipe()
        m1_result = run_m1_from_recipe(recipe)
        db = PropertyDatabase()
        params = m1_result.parameters
        props = db.update_for_conditions(
            T_oil=params.formulation.T_oil,
            c_agarose=params.formulation.c_agarose,
            c_chitosan=params.formulation.c_chitosan,
            c_span80=params.formulation.c_span80,
        )
        trust = assess_trust(m1_result, params, props)
        m1_contract = export_for_module2(m1_result, trust, props=props)

        # Pre-register the upstream M1 node so depends_on edges work.
        graph = ResultGraph()
        graph.add_node(
            ResultNode(
                node_id="M1",
                stage="M1",
                label="M1 fabrication",
                manifest=ModelManifest(
                    model_name="M1.legacy_pipeline",
                    evidence_tier=ModelEvidenceTier.SEMI_QUANTITATIVE,
                ),
            )
        )

        steps = default_protein_a_functionalization_steps()
        orch = ModificationOrchestrator()
        orch.run(m1_contract, steps, graph=graph, upstream_node_id="M1")

        m2_nodes = [n for n in graph.nodes.values() if n.stage == "M2"]
        # Expect one node per modification step (5 steps default, plus
        # washes — exact count depends on the default sequence).
        assert len(m2_nodes) == len(steps), (
            f"expected {len(steps)} M2 sub-step nodes; got {len(m2_nodes)}: "
            f"{[n.node_id for n in m2_nodes]}"
        )
        # Edges should chain step 1 → step 2 → ... → step n.
        m2_edges = [e for e in graph.edges if e.relation == "m2_step_sequence"]
        assert len(m2_edges) == len(steps)

    def test_modification_orchestrator_without_graph_unchanged(self):
        """Default behavior (graph=None) must not mutate any global state."""
        from dpsim.lifecycle.orchestrator import (
            default_protein_a_functionalization_steps,
        )
        from dpsim.module2_functionalization.orchestrator import (
            ModificationOrchestrator,
        )
        from dpsim.pipeline.orchestrator import export_for_module2
        from dpsim.properties.database import PropertyDatabase
        from dpsim.lifecycle import run_m1_from_recipe
        from dpsim.core.process_recipe import default_affinity_media_recipe
        from dpsim.trust import assess_trust

        recipe = default_affinity_media_recipe()
        m1_result = run_m1_from_recipe(recipe)
        db = PropertyDatabase()
        params = m1_result.parameters
        props = db.update_for_conditions(
            T_oil=params.formulation.T_oil,
            c_agarose=params.formulation.c_agarose,
            c_chitosan=params.formulation.c_chitosan,
            c_span80=params.formulation.c_span80,
        )
        trust = assess_trust(m1_result, params, props)
        m1_contract = export_for_module2(m1_result, trust, props=props)

        steps = default_protein_a_functionalization_steps()
        orch = ModificationOrchestrator()
        result = orch.run(m1_contract, steps)  # no graph kwarg
        assert result is not None
        assert len(result.modification_history) == len(steps)
