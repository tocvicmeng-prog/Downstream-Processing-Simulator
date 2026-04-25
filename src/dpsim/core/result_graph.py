"""Result graph for M1 -> M2 -> M3 lifecycle runs."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from dpsim.datatypes import ModelEvidenceTier, ModelManifest


@dataclass
class ResultNode:
    """A process result node with optional solver payload and manifest."""

    node_id: str
    stage: str
    label: str
    payload: Any = None
    manifest: ModelManifest | None = None
    diagnostics: dict[str, Any] = field(default_factory=dict)
    wet_lab_caveats: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class ResultEdge:
    """Directed dependency between process result nodes."""

    source: str
    target: str
    relation: str


@dataclass
class ResultGraph:
    """Small directed graph capturing scientific handoffs across modules."""

    nodes: dict[str, ResultNode] = field(default_factory=dict)
    edges: list[ResultEdge] = field(default_factory=list)

    def add_node(self, node: ResultNode) -> None:
        """Add or replace a node by id."""
        self.nodes[node.node_id] = node

    def add_edge(self, source: str, target: str, relation: str) -> None:
        """Record a typed dependency between two nodes."""
        if source not in self.nodes:
            raise KeyError(f"Unknown source node {source!r}")
        if target not in self.nodes:
            raise KeyError(f"Unknown target node {target!r}")
        self.edges.append(ResultEdge(source=source, target=target, relation=relation))

    def model_manifests(self) -> list[ModelManifest]:
        """Return all manifests attached directly to nodes."""
        return [node.manifest for node in self.nodes.values() if node.manifest is not None]

    def weakest_evidence_tier(self) -> ModelEvidenceTier:
        """Return the weakest evidence tier across node manifests."""
        manifests = self.model_manifests()
        if not manifests:
            return ModelEvidenceTier.UNSUPPORTED
        order = list(ModelEvidenceTier)
        worst = max(order.index(m.evidence_tier) for m in manifests)
        return order[worst]

    def as_summary(self) -> dict[str, Any]:
        """JSON-serializable graph summary for dossiers and handovers."""
        return {
            "nodes": [
                {
                    "node_id": n.node_id,
                    "stage": n.stage,
                    "label": n.label,
                    "manifest": None if n.manifest is None else {
                        "model_name": n.manifest.model_name,
                        "evidence_tier": n.manifest.evidence_tier.value,
                        "calibration_ref": n.manifest.calibration_ref,
                        "valid_domain": n.manifest.valid_domain,
                    },
                    "diagnostics": n.diagnostics,
                    "assumptions": [] if n.manifest is None else list(n.manifest.assumptions),
                    "wet_lab_caveats": list(n.wet_lab_caveats),
                }
                for n in self.nodes.values()
            ],
            "edges": [edge.__dict__ for edge in self.edges],
            "weakest_evidence_tier": self.weakest_evidence_tier().value,
        }
