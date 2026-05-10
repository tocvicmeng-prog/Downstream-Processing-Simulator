"""Shared operator-flow rendering helpers for lifecycle stages."""

from __future__ import annotations

import html


def operator_flow_row_html(row: dict[str, str]) -> str:
    """Return one stage-flow cell as HTML."""

    state = row["state"]
    color = {
        "ready": "var(--dps-green-500)",
        "warning": "var(--dps-amber-500)",
        "blocked": "var(--dps-red-600)",
        "pending": "var(--dps-text-dim)",
    }.get(state, "var(--dps-text-dim)")
    return (
        '<div style="background:var(--dps-surface);'
        'border:1px solid var(--dps-border);border-radius:4px;'
        'padding:8px 9px;min-width:0;">'
        '<div class="dps-mono" style="font-size:10.5px;'
        f'color:{color};text-transform:uppercase;font-weight:600;">'
        f"{html.escape(state)}</div>"
        '<div style="font-size:12.5px;color:var(--dps-text);'
        'font-weight:600;margin-top:2px;">'
        f"{html.escape(row['step'])}</div>"
        '<div style="font-size:11.5px;color:var(--dps-text-dim);'
        'line-height:1.35;margin-top:2px;">'
        f"{html.escape(row['detail'])}</div></div>"
    )


def operator_flow_html(rows: list[dict[str, str]], *, css_class: str) -> str:
    """Return a complete operator-flow strip."""

    body = "".join(operator_flow_row_html(row) for row in rows)
    return f'<div class="{html.escape(css_class)}">{body}</div>'


__all__ = ["operator_flow_html", "operator_flow_row_html"]
