"""Tier-routing CI gate (W-081, v0.8.9).

Closes audit defect S-10 / A-15 from the v0.8.5 e2e audit: at v0.8.7
many UI panels surfaced numeric values via bare ``st.metric`` calls
that bypass the decision-grade tier ladder. v0.8.8 W-080 fixed the
high-traffic ones; this gate enforces no NEW bare ``.metric(`` calls
land outside the documented baseline.

The gate walks user-facing UI modules for ``.metric(`` call sites and
asserts that none bypass the central decision-grade wrapper.

The companion AST gate `test_widget_mounting.py` (W-073) catches
*structural* widget orphans; this gate catches *policy-tier* drift.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parents[2]
SCAN_ROOTS = (
    REPO_ROOT / "src" / "dpsim" / "visualization",
    REPO_ROOT / "src" / "dpsim" / "suggestions",
)

# Pattern: bare `.metric(` call. Captures both `st.metric(...)` and
# `_pm1.metric(...)` (column object metric calls). The intention is to
# flag every numeric display that bypasses `render_metric` /
# `render_decision_grade_annotation`.
#
# Excludes the tier-routed render_metric helper itself (defined in
# decision_grade_render.py) — that file declares the wrapper.
_METRIC_PATTERN = re.compile(r"\.metric\s*\(")

# Baseline — zero bare `.metric(` call sites outside the central wrapper.
# Any numeric display should route through `render_metric(...)` from
# decision_grade_render, or use a non-metric presentation when it is metadata
# rather than a decision-bearing value.
_BASELINE_BARE_METRICS = 0


def _walk_metric_callsites() -> list[tuple[Path, int, str]]:
    """Walk user-facing UI trees and return every `.metric(` line.

    Excludes the test scaffolding directory and the
    decision_grade_render.py module which IS the wrapper.
    """
    findings: list[tuple[Path, int, str]] = []
    for root in SCAN_ROOTS:
        for path in root.rglob("*.py"):
            if path.name == "decision_grade_render.py":
                continue
            try:
                text = path.read_text(encoding="utf-8")
            except UnicodeDecodeError:
                continue
            for i, line in enumerate(text.splitlines(), start=1):
                if _METRIC_PATTERN.search(line):
                    # Skip lines that are clearly the tier-routed wrapper:
                    # the `_rm_*.metric(...)` aliases assigned earlier in
                    # the file from `render_metric`. Heuristic: if `_rm`
                    # prefix appears, it's the wrapper alias.
                    if "_rm" in line and "_rm_" in line:
                        continue
                    findings.append((path, i, line.strip()))
    return findings


def test_metric_callsite_count_does_not_exceed_baseline():
    """Tier-routing CI gate.

    Asserts user-facing UI modules have no bare `.metric(` call sites.
    To add a new metric, route it through `render_metric` from
    `decision_grade_render` (carries OutputType + tier), or use a
    non-metric presentation for metadata.
    """
    findings = _walk_metric_callsites()
    n = len(findings)
    if n > _BASELINE_BARE_METRICS:
        msg = (
            f"Bare `.metric(` callsite count {n} exceeds baseline "
            f"{_BASELINE_BARE_METRICS}. New numeric displays must "
            "route through `render_metric` from "
            "`dpsim.visualization.decision_grade_render` (carries "
            "OutputType + tier per the decision-grade ladder).\n\n"
            "New callsites since baseline:\n"
            + "\n".join(
                f"  - {p.relative_to(REPO_ROOT)}:{ln} → {src}"
                for p, ln, src in findings[_BASELINE_BARE_METRICS:]
            )
        )
        pytest.fail(msg)


def test_baseline_metric_count_is_at_documented_level():
    """Sanity — the baseline is set correctly (no off-by-one)."""
    findings = _walk_metric_callsites()
    assert len(findings) <= _BASELINE_BARE_METRICS, (
        f"Found {len(findings)} bare metrics; baseline = "
        f"{_BASELINE_BARE_METRICS}. If you removed one, lower the "
        "baseline."
    )
