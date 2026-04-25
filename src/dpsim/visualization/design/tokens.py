"""Design tokens — Python constants mirroring ``tokens.css``.

The two surfaces (``TOKENS`` dict + ``tokens.css`` file) must stay in
sync. ``tests/test_design_tokens_match.py`` enforces this — every
``--dps-*`` variable referenced by ``chrome.py`` must exist here AND
in the CSS file.

Why two surfaces? The CSS file is injected globally so HTML emitted
via ``st.html`` can use ``var(--dps-accent)`` etc. The Python dict is
used by server-side renderers that build SVG strings inline (e.g.
``chrome.mini_histogram``) — those strings are interpolated as plain
hex values, not CSS variables, so colour reasoning works without a
DOM.
"""

from __future__ import annotations

from pathlib import Path
from typing import Final

import streamlit as st

# Slate scale — neutrals.
_SLATE: Final[dict[str, str]] = {
    "slate-50": "#F8FAFC",
    "slate-100": "#F1F5F9",
    "slate-200": "#E2E8F0",
    "slate-300": "#CBD5E1",
    "slate-400": "#94A3B8",
    "slate-500": "#64748B",
    "slate-600": "#475569",
    "slate-700": "#334155",
    "slate-800": "#1E293B",
    "slate-900": "#0F172A",
    "slate-950": "#020617",
}

# Teal — sole accent.
_TEAL: Final[dict[str, str]] = {
    "teal-300": "#5EEAD4",
    "teal-400": "#2DD4BF",
    "teal-500": "#14B8A6",
    "teal-600": "#0D9488",
}

# Semantic / evidence-tier colours.
_SEMANTIC: Final[dict[str, str]] = {
    "green-500": "#22C55E",
    "green-600": "#16A34A",
    "amber-500": "#F59E0B",
    "orange-500": "#F97316",
    "red-600": "#DC2626",
    "sky-600": "#0284C7",
}

# Type stack (matches DESIGN.md §Typography).
_FONTS: Final[dict[str, str]] = {
    "font-sans": (
        '"Geist", -apple-system, BlinkMacSystemFont, "Segoe UI", '
        "system-ui, sans-serif"
    ),
    "font-mono": '"Geist Mono", "JetBrains Mono", Menlo, monospace',
    "font-code": '"JetBrains Mono", "Geist Mono", Menlo, monospace',
}

# Border-radius scale.
_RADIUS: Final[dict[str, str]] = {
    "r-1": "2px",
    "r-2": "4px",
    "r-3": "6px",
}

# Spacing scale (8px base, 4px half-unit per DESIGN.md §Spacing).
_SPACING: Final[dict[str, str]] = {
    "s-0": "2px",
    "s-1": "4px",
    "s-2": "8px",
    "s-3": "12px",
    "s-4": "16px",
    "s-5": "20px",
    "s-6": "24px",
    "s-8": "32px",
    "s-10": "40px",
    "s-12": "48px",
}

# Dark theme (default) — surface assignments.
_DARK_SURFACES: Final[dict[str, str]] = {
    "bg": _SLATE["slate-950"],
    "surface": _SLATE["slate-900"],
    "surface-2": _SLATE["slate-800"],
    "surface-3": _SLATE["slate-700"],
    "border": "rgba(71, 85, 105, 0.55)",
    "border-strong": "rgba(148, 163, 184, 0.30)",
    "text": _SLATE["slate-50"],
    "text-muted": _SLATE["slate-400"],
    "text-dim": _SLATE["slate-500"],
    "accent": _TEAL["teal-400"],
    "accent-hover": _TEAL["teal-300"],
    "accent-soft": "rgba(45, 212, 191, 0.12)",
}

# Public flat token map. Keys are the DESIGN.md token names without the
# `--dps-` CSS prefix. Use ``TOKENS["accent"]`` from Python; use
# ``var(--dps-accent)`` from CSS / inline styles.
TOKENS: Final[dict[str, str]] = {
    **_SLATE,
    **_TEAL,
    **_SEMANTIC,
    **_FONTS,
    **_RADIUS,
    **_SPACING,
    **_DARK_SURFACES,
}

CSS_PATH: Final[Path] = Path(__file__).parent / "tokens.css"


def load_css() -> str:
    """Return the contents of ``tokens.css`` as a string.

    Read once per call; Streamlit caches via ``@st.cache_data`` upstream
    when the caller wraps ``inject_global_css`` (see ``shell.shell``).
    """
    return CSS_PATH.read_text(encoding="utf-8")


def inject_global_css() -> None:
    """Inject ``tokens.css`` as a single ``<style>`` block.

    v0.4.18 (P10): switched from ``st.html`` to
    ``st.markdown(unsafe_allow_html=True)``. Streamlit 1.55 sanitises
    ``<style>`` tags out of ``st.html`` output (verified empirically:
    the injected ``<style>`` element is dropped before reaching the
    DOM, leaving the page unstyled). Markdown's ``unsafe_allow_html``
    path preserves ``<style>`` blocks intact.

    Markdown does process the inner text for italics/bold, but Python-
    Markdown and Streamlit's renderer skip that inside raw ``<style>``
    blocks, so ``*=`` attribute selectors survive. The single such
    selector in tokens.css (``div[style*="border: 1px solid"]``) has
    been verified to round-trip correctly.
    """
    css = load_css()
    st.markdown(f"<style>\n{css}\n</style>", unsafe_allow_html=True)
