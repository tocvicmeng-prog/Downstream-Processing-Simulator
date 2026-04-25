"""Vessel-mode roadmap strip (v0.4.17, milestone P3).

The L1 PBE solver currently supports two emulsification modes:
``stirred_vessel`` and ``rotor_stator_legacy`` (see
``EmulsificationParameters.mode`` in ``dpsim.datatypes``). The v9.0
roadmap adds Membrane and Microfluidic. To set scientifically honest
expectations — and follow the canonical Direction-A reference which
shows all four modes — this module emits a small "Planned" strip
underneath the binary Hardware-Mode radio.

Rendering only — does NOT change the radio's return value or session
key. The radio remains the authoritative selector.
"""

from __future__ import annotations

import streamlit as st


def render_planned_modes_strip() -> None:
    """Render the "Planned: Membrane (M1.5) · Microfluidic (M2.0)" strip.

    Visual cue only. Tells the user the canonical Direction-A reference
    surfaces these modes intentionally — they're on the roadmap but the
    L1 kernel is not yet wired up, so they are not selectable. Honest
    UX, no science-claim violation.
    """
    st.html(
        '<div class="dps-mono" style="display:flex;align-items:center;'
        "gap:8px;margin-top:6px;padding:4px 10px;"
        "background:var(--dps-surface-2);"
        "border:1px dashed var(--dps-border);border-radius:3px;"
        'font-size:10.5px;color:var(--dps-text-dim);">'
        '<span style="color:var(--dps-text-muted);font-weight:600;'
        'letter-spacing:0.04em;">PLANNED</span>'
        '<span style="opacity:0.65;">Membrane · M1.5</span>'
        '<span style="opacity:0.4;">·</span>'
        '<span style="opacity:0.65;">Microfluidic · M2.0</span>'
        '<span style="margin-left:auto;opacity:0.6;">L1 PBE kernel '
        "not yet wired</span>"
        "</div>"
    )
