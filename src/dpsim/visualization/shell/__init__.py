"""DPSim v0.4.0 Direction-A shell.

Composes the new top app bar + stage spine + 2-column main grid +
sticky run rail. Wraps (does not replace) the existing
``tabs.render_tab_m1 / m2 / m3`` and ``ui_workflow.render_lifecycle_*``
panels — those remain the source of truth for stage content; the shell
provides the chrome and navigation around them.
"""

from __future__ import annotations

from dpsim.visualization.shell.autowire import (
    autowire_shell_state,
    derive_stage_status,
)
from dpsim.visualization.shell.shell import (
    STAGE_ORDER,
    StageId,
    ThemeMode,
    get_active_stage,
    get_theme,
    render_shell,
    render_stage_spine,
    render_top_bar,
    set_active_stage,
    set_theme,
)
from dpsim.visualization.shell.triptych import (
    ShellDirection,
    TriptychFocus,
    get_direction,
    get_triptych_focus,
    render_direction_switch,
    render_triptych,
    set_direction,
    set_triptych_focus,
)

__all__ = [
    "STAGE_ORDER",
    "ShellDirection",
    "StageId",
    "ThemeMode",
    "TriptychFocus",
    "autowire_shell_state",
    "derive_stage_status",
    "get_active_stage",
    "get_direction",
    "get_theme",
    "get_triptych_focus",
    "render_direction_switch",
    "render_shell",
    "render_stage_spine",
    "render_top_bar",
    "render_triptych",
    "set_active_stage",
    "set_direction",
    "set_theme",
    "set_triptych_focus",
]
