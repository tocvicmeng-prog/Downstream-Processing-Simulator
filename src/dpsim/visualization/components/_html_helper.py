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

Routing rule (auto, post-2026-05-04 Streamlit-UI regression diagnosis):

  * **Full HTML documents** (start with ``<!doctype>`` or ``<html>``) MUST
    use the iframe path — they carry their own ``<head>``/``<style>``/
    ``<body>`` and cannot be inlined into the host page. DOMPurify on
    ``st.html`` strips the document wrapper and breaks rendering.
  * **HTML fragments** (start with any other tag, or with whitespace +
    a tag) use ``st.html`` with a sized wrapper ``<div>``.

All five visualisation cross-section assets (impeller_xsec_v*, column_xsec)
are full HTML documents and therefore correctly route to the iframe path.
The ``DPSIM_USE_LEGACY_HTML=1`` env-var override remains as a global
escape hatch (forces iframe regardless of content shape).
"""

from __future__ import annotations

import logging
import os
import re
from typing import Final

import streamlit as st

logger = logging.getLogger(__name__)

_LEGACY_OVERRIDE_ENV: Final[str] = "DPSIM_USE_LEGACY_HTML"

# Match a full HTML document — any leading whitespace, then <!doctype or
# <!DOCTYPE or <html (case-insensitive on the tag name). Captures the
# Streamlit-relevant cases without false positives on inline fragments.
_FULL_DOCUMENT_RE: Final[re.Pattern[str]] = re.compile(
    r"\A\s*(?:<!doctype\b|<html\b)", re.IGNORECASE,
)


def _use_legacy_api() -> bool:
    """True iff the operator has opted into the legacy components.v1.html API."""
    return os.environ.get(_LEGACY_OVERRIDE_ENV, "").strip() == "1"


def _is_full_document(html: str) -> bool:
    """True iff ``html`` starts with a doctype declaration or <html> tag.

    Full documents have their own head/body/style/script structure and
    cannot be inlined into a host page — they MUST use the iframe path.
    """
    return bool(_FULL_DOCUMENT_RE.match(html))


def render_inline_html(
    html: str,
    *,
    height_px: int,
    scrolling: bool = False,
) -> None:
    """Render inline HTML in a Streamlit container with sizing.

    Routing:
      * Full HTML documents → ``st.components.v1.html`` (iframe).
      * HTML fragments      → ``st.html`` with a sized wrapper ``<div>``.
      * ``DPSIM_USE_LEGACY_HTML=1`` env var forces the iframe path
        regardless of content shape (escape hatch).
      * Older Streamlit without ``st.html`` falls back to iframe.

    Args:
        html: raw HTML string. Caller is responsible for escaping any
            untrusted content (the visualisation components only render
            data they themselves generate from validated inputs).
        height_px: desired component height in pixels. With ``st.html``
            this becomes a CSS ``min-height`` on a wrapper div; with
            the iframe path this is the ``height=`` parameter.
        scrolling: when True, the wrapper div / iframe permits scrolling.

    Returns:
        None — Streamlit emits the component as a side effect.
    """
    use_iframe = (
        _use_legacy_api()
        or not hasattr(st, "html")
        or _is_full_document(html)
    )
    if use_iframe:
        # Iframe path: required for full HTML documents (those carry their
        # own head/body/script), and the explicit override / older-Streamlit
        # fallback still works.
        from streamlit.components.v1 import html as _legacy_html
        _legacy_html(html, height=height_px, scrolling=scrolling)
        return

    sized_html = (
        f'<div style="min-height:{int(height_px)}px;width:100%;'
        f'overflow:{"auto" if scrolling else "hidden"};">'
        f'{html}'
        f'</div>'
    )
    # unsafe_allow_javascript=True is required for HTML fragments that
    # ship inline JS (e.g., RAF animation loops). HTML content originates
    # from trusted in-process generators (no user input is interpolated).
    st.html(sized_html, unsafe_allow_javascript=True)


__all__ = ["render_inline_html"]
