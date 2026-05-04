"""Shim for the W-017 / Streamlit st.components.v1.html → st.html migration.

Reference: docs/handover/HANDOVER_tier_0_close_2026-05-04.md §6 (W-017
deferred from Tier 0 with deadline 2026-06-01).

The deprecated ``streamlit.components.v1.html`` renders inline HTML in an
iframe with ``height``/``scrolling`` parameters and full CSS isolation.
The replacement ``st.html`` (Streamlit ≥ 1.39):

  * Renders HTML inline (no iframe), with DOMPurify sanitisation.
  * Has no ``height`` or ``scrolling`` parameter — sizing is done via the
    HTML's own CSS.
  * Strips inline ``<script>`` blocks unless ``unsafe_allow_javascript=True``.

The ``impeller_xsec_v*`` and ``column_xsec`` components carry SVG markup
plus a small RAF-driven animation loop, so they need
``unsafe_allow_javascript=True`` and a wrapper ``<div>`` to recreate the
height behavior. DOMPurify in recent Streamlit releases preserves SVG
attributes the components depend on; if a future Streamlit version
tightens sanitisation, set the env var
``DPSIM_USE_LEGACY_HTML=1`` to fall back to ``st.components.v1.html``
for one release while a permanent fix lands.
"""

from __future__ import annotations

import logging
import os
from typing import Final

import streamlit as st

logger = logging.getLogger(__name__)

_LEGACY_OVERRIDE_ENV: Final[str] = "DPSIM_USE_LEGACY_HTML"


def _use_legacy_api() -> bool:
    """True iff the operator has opted into the legacy components.v1.html API."""
    return os.environ.get(_LEGACY_OVERRIDE_ENV, "").strip() == "1"


def render_inline_html(
    html: str,
    *,
    height_px: int,
    scrolling: bool = False,
) -> None:
    """Render inline HTML in a Streamlit container with sizing.

    Preferred path: ``st.html`` with a wrapper ``<div>`` that recreates
    the height + overflow behavior of the legacy iframe API. Inline
    JavaScript is enabled (the visualisation components depend on
    ``requestAnimationFrame`` for animations).

    Fallback paths:
      * ``DPSIM_USE_LEGACY_HTML=1``  → ``st.components.v1.html`` (deprecated)
      * ``st.html`` not available    → ``st.components.v1.html`` (older Streamlit)

    Args:
        html: raw HTML string. Caller is responsible for escaping any
            untrusted content (the visualisation components only render
            data they themselves generate from validated inputs).
        height_px: desired component height in pixels. With ``st.html``
            this becomes a CSS ``min-height`` on a wrapper div; with
            the legacy iframe API this is the iframe ``height=``.
        scrolling: when True, the wrapper div / iframe permits scrolling.

    Returns:
        None — Streamlit emits the component as a side effect.
    """
    if _use_legacy_api() or not hasattr(st, "html"):
        # Legacy path: iframe-based. Suppresses none of the visual behaviour
        # but emits a Streamlit deprecation warning at call time.
        from streamlit.components.v1 import html as _legacy_html
        _legacy_html(html, height=height_px, scrolling=scrolling)
        return

    sized_html = (
        f'<div style="min-height:{int(height_px)}px;width:100%;'
        f'overflow:{"auto" if scrolling else "hidden"};">'
        f'{html}'
        f'</div>'
    )
    # unsafe_allow_javascript=True is required for the visualisation
    # components' RAF-driven animation loops; HTML content originates
    # from trusted in-process generators (no user input is interpolated).
    st.html(sized_html, unsafe_allow_javascript=True)


__all__ = ["render_inline_html"]
