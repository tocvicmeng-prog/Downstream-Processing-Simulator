"""M3 tab sub-modules.

W-087 (v0.8.9) — proof-of-pattern split of the 1198-LOC ``tab_m3.py``.
The full IA refactor (every section into its own module) is queued
for v1.0; this directory hosts the first extraction.
"""

from .method_conditions_section import render_method_conditions_section

__all__ = ["render_method_conditions_section"]
