"""Evidence-tier rollup — lifecycle min badge + per-stage breakdown.

Reads the ``RunReport.compute_min_tier`` (already enforced by the
inheritance rule M1 → M2 → M3) and surfaces:

- The lifecycle-aggregated badge in the top bar (Direction A).
- A per-stage breakdown panel that pops out on hover / click (so the
  user can see WHICH stage caps the lifecycle min).

Per the SA Q3 sign-off in ``SA_v0_4_0_RUSHTON_FIDELITY.md``: show the
lifecycle min as the headline, with the per-stage breakdown as the
diagnostic drill-down. Never show only the per-stage chips — that
invites the eye to read the highest tier as the headline, which is
the inheritance violation the v9.0 evidence model is built to prevent.
"""

from __future__ import annotations

from dpsim.visualization.evidence.rollup import (
    StageEvidence,
    aggregate_min_tier,
    render_evidence_summary,
    render_top_bar_badge,
)

__all__ = [
    "StageEvidence",
    "aggregate_min_tier",
    "render_evidence_summary",
    "render_top_bar_badge",
]
