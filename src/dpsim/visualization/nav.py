"""Explicit Streamlit navigation (v0.3.0 module B7).

Originally planned in v9.0 milestone M8 as a replacement for Streamlit's
auto-listing of every file under ``pages/``. Today the auto-listing is hidden
via the ``[data-testid="stSidebarNav"]`` CSS selector in ``app.py``, and the
hidden detail pages (``reagent_detail``, ``suggestion_detail``) are reached
via query-parameter links built by ``ui_links``. Together those two paths
satisfy the original M8 goals (hide auto-list, expose hidden pages via URL),
so a full ``st.navigation`` refactor is no longer required.

This module provides a ``build_navigation`` helper that callers may use when
they want explicit ``st.Page`` registration. ``app.py`` does not call it
today; the function exists so the API surface is non-throwing and the
module-level ``NotImplementedError`` stub is retired (closes the v0.2/v0.3
debt flagged in the architect-coherence audit, D1).
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import streamlit as st


def build_navigation() -> Any:
    """Build a hidden-position ``st.navigation`` for the dpsim UI.

    Returns:
        A Streamlit ``Navigation`` object configured with:
            - ``app.py`` as the default landing page (``url_path=""``).
            - ``pages/reagent_detail.py`` reachable at ``/reagent_detail``.
            - ``pages/suggestion_detail.py`` reachable at ``/suggestion_detail``.

        The navigation is registered with ``position="hidden"`` so it does
        not duplicate the sidebar listing (which is suppressed via CSS in
        ``app.py``). Returns ``None`` on Streamlit versions that do not
        expose ``st.navigation`` / ``st.Page`` (< 1.36).

    Note:
        ``app.py`` does not call this helper as of v0.3.0; it is provided
        for callers that want explicit page registration in a multi-app
        setup. Wiring ``app.py`` to consume it is deferred until a
        multi-page UX redesign is on the roadmap.
    """
    if not (hasattr(st, "navigation") and hasattr(st, "Page")):
        return None
    base = Path(__file__).parent
    pages = [
        st.Page(
            str(base / "app.py"),
            title="dpsim",
            url_path="",
            default=True,
        ),
        st.Page(
            str(base / "pages" / "reagent_detail.py"),
            title="Reagent detail",
            url_path="reagent_detail",
        ),
        st.Page(
            str(base / "pages" / "suggestion_detail.py"),
            title="Suggestion detail",
            url_path="suggestion_detail",
        ),
    ]
    return st.navigation(pages, position="hidden")


__all__ = ["build_navigation"]
