"""Smoke tests for the v0.4.0 UI chrome primitives.

Covers M-001 (design.tokens) and M-002 (design.chrome). Confirms that
the new modules import cleanly, that every chrome helper produces
HTML containing the expected DESIGN.md tokens, and that the
``--dps-*`` variables referenced by the helpers exist in
``tokens.css`` (architecture spec §4.11 R-08).
"""

from __future__ import annotations

import re

import pytest

from dpsim.datatypes import ModelEvidenceTier
from dpsim.visualization.design import (
    CSS_PATH,
    TOKENS,
    chrome,
)


def test_tokens_dict_has_all_dark_surface_assignments() -> None:
    for key in (
        "bg",
        "surface",
        "surface-2",
        "surface-3",
        "border",
        "border-strong",
        "text",
        "text-muted",
        "text-dim",
        "accent",
        "accent-hover",
        "accent-soft",
    ):
        assert key in TOKENS, f"missing token: {key}"


def test_tokens_css_file_exists_and_loads() -> None:
    assert CSS_PATH.exists()
    css = CSS_PATH.read_text(encoding="utf-8")
    assert "--dps-accent:" in css
    assert "--dps-bg:" in css
    assert ".dps-light" in css
    assert "@import url('https://fonts.googleapis.com/css2?family=Geist" in css


def test_every_chrome_dps_var_exists_in_tokens_css() -> None:
    """Architecture spec §4.11 R-08 — guard against drift.

    Every ``--dps-*`` variable referenced by chrome helpers must be
    defined in tokens.css. We sample the helpers' output and grep for
    the variable names, then confirm each is declared in the CSS.
    """
    css = CSS_PATH.read_text(encoding="utf-8")
    sample_html = "\n".join([
        chrome.eyebrow("test"),
        chrome.eyebrow("test", accent=True),
        chrome.chip("test"),
        chrome.evidence_badge(ModelEvidenceTier.CALIBRATED_LOCAL),
        chrome.evidence_badge(ModelEvidenceTier.SEMI_QUANTITATIVE, compact=True),
        chrome.stage_node(
            index=1, label="x", status="active", active=True,
            evidence=ModelEvidenceTier.CALIBRATED_LOCAL,
        ),
        chrome.card(title="t", eyebrow_text="e", body="<p>x</p>"),
        chrome.metric_value("78.2", unit="µm", delta="+2.4", delta_direction="up"),
        chrome.mini_histogram([1.0, 2.0, 3.0, 2.0, 1.0]),
        chrome.breakthrough(),
    ])
    referenced = set(re.findall(r"var\(--dps-[a-z0-9-]+\)", sample_html))
    for ref in referenced:
        var_name = ref.removeprefix("var(").removesuffix(")")
        assert f"{var_name}:" in css, f"chrome references {ref} but tokens.css does not declare it"


@pytest.mark.parametrize(
    "tier",
    list(ModelEvidenceTier),
)
def test_evidence_badge_renders_for_every_tier(tier: ModelEvidenceTier) -> None:
    html = chrome.evidence_badge(tier)
    assert "<span" in html
    # The badge must mention a colour bound to the tier (token reference).
    assert "var(--dps-" in html or "color-mix" in html


def test_stage_node_active_uses_accent_ring() -> None:
    html = chrome.stage_node(
        index=2, label="M1 — Fabrication", status="active",
        active=True, evidence=ModelEvidenceTier.CALIBRATED_LOCAL,
    )
    assert "var(--dps-accent)" in html
    assert "M1 — Fabrication" in html


def test_stage_node_complete_renders_check_mark() -> None:
    html = chrome.stage_node(
        index=1, label="Target", status="valid",
        active=False, evidence=None, complete=True,
    )
    assert "✓" in html


def test_card_without_header_has_no_header_strip() -> None:
    html = chrome.card(body="<p>x</p>")
    assert "<header" not in html
    assert "<p>x</p>" in html


def test_card_with_header_has_eyebrow_and_title() -> None:
    html = chrome.card(eyebrow_text="Polymer family", title="Drives downstream rendering", body="<p>x</p>")
    assert "POLYMER FAMILY" in html.upper()
    assert "Drives downstream rendering" in html


def test_metric_value_delta_direction_colours() -> None:
    up = chrome.metric_value("78.2", unit="µm", delta="+2.4", delta_direction="up")
    down = chrome.metric_value("78.2", unit="µm", delta="-2.4", delta_direction="down")
    none = chrome.metric_value("78.2", unit="µm")
    assert "var(--dps-green-500)" in up
    assert "▲" in up
    assert "var(--dps-red-600)" in down
    assert "▼" in down
    assert "var(--dps-green-500)" not in none
    assert "var(--dps-red-600)" not in none


def test_mini_histogram_bin_count_matches_input() -> None:
    bins = [1.0, 2.5, 4.0, 3.0, 1.5]
    html = chrome.mini_histogram(bins)
    # One <rect> per bin plus the baseline line.
    assert html.count("<rect") == len(bins)


def test_breakthrough_synthetic_curve_has_dbc_marker() -> None:
    html = chrome.breakthrough(dbc_marker_at=0.55)
    assert "<svg" in html
    assert "circle" in html  # DBC10 indicator
    assert "C/C₀" in html


def test_pipeline_spine_with_seven_stages_renders_six_arrows() -> None:
    stages = [
        chrome.StageSpec(id=sid, label=lbl, status="pending")
        for sid, lbl in [
            ("target", "Target profile"),
            ("m1", "M1 — Fabrication"),
            ("m2", "M2 — Functionalisation"),
            ("m3", "M3 — Column"),
            ("run", "Run lifecycle"),
            ("validation", "Validation"),
            ("calibrate", "Calibration"),
        ]
    ]
    html = chrome.pipeline_spine(stages, active_id="m1")
    assert html.count("→") == 6
    assert "M1 — Fabrication" in html


def test_html_escapes_user_input_for_safety() -> None:
    """Recipe field names with `<`, `>`, `&` must not break the page."""
    danger = '<script>alert("x")</script>'
    html = chrome.chip(danger)
    assert "<script>" not in html
    assert "&lt;script&gt;" in html


def test_impeller_xsec_module_imports_and_asset_exists() -> None:
    """M-007 smoke — module imports and the HTML asset is on disk."""
    from dpsim.visualization.components import render_impeller_xsec
    from dpsim.visualization.components.impeller_xsec import _ASSET_PATH

    assert _ASSET_PATH.exists()
    html = _ASSET_PATH.read_text(encoding="utf-8")
    # Templating placeholders must all be present (one per substitution).
    for placeholder in (
        "__RPM__",
        "__WIDTH__",
        "__HEIGHT__",
        "__IMPELLER_D_MM__",
        "__TANK_D_MM__",
        "__LIQUID_VOLUME_ML__",
        "__N_BLADES__",
        "__THEME__",
    ):
        assert placeholder in html, f"missing placeholder {placeholder} in asset"
    # SA prescriptions — sanity grep that the key fixes landed.
    assert "Trailing-vortex" in html or "trailing" in html.lower()
    assert "f_pass" in html
    assert "Re_imp" in html
    assert "Wu & Patterson" in html
    assert "B/T" in html or "baffle" in html.lower()
    # Defensive: render_impeller_xsec is importable.
    assert callable(render_impeller_xsec)
