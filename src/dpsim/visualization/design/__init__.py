"""DPSim v0.4.0 design system package.

Single source of truth for design tokens (palette, type, spacing) and
the chrome-rendering primitives that consume them. Spec:
``docs/handover/ARCH_v0_4_0_UI_OPTIMIZATION.md``.
"""

from __future__ import annotations

from dpsim.visualization.design.tokens import (
    CSS_PATH,
    TOKENS,
    inject_global_css,
    load_css,
)

__all__ = [
    "CSS_PATH",
    "TOKENS",
    "inject_global_css",
    "load_css",
]
