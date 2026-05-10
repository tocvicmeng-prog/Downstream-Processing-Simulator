"""Wet-lab YAML calibration-campaign ingestion UI panel.

B-1r / W-057 — v0.8.4. Resolves audit defect C6 (Phase 1 §6).

The pre-v0.8.4 UI had two unlabelled file uploaders and no clear path
for the wet-lab YAML campaign ingestion documented in
``data/wetlab_calibration_examples/``. This panel:

1. Renders a clearly-labelled "Upload wet-lab calibration campaign (YAML)"
   uploader in its own card.
2. Calls :func:`dpsim.calibration.wetlab_ingestion.load_campaign` to
   parse the campaign.
3. Calls :func:`dpsim.calibration.wetlab_ingestion.apply_campaign` to
   produce an ``IngestionResult`` that names the affected profile keys
   + the tier-promotion diff per profile.
4. Surfaces a tier-promotion preview before any state is committed.
5. On the user clicking **Apply**, persists the updated profiles in
   ``st.session_state['_cal_store']`` (existing key from
   ``ui_workflow.py:881``) and flips ``st.session_state['_calibration_loaded']``
   so the tier banner reflects the new state.

This panel is the canonical "wet-lab handshake" UI surface that
promotes K_geom / ν / coupling-yield outputs from SEMI_QUANTITATIVE
INTERVAL to CALIBRATED_LOCAL NUMBER under the README guardrail.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional

import streamlit as st

from dpsim.calibration.wetlab_ingestion import (
    IngestionResult,
    WetlabCampaign,
    apply_campaign,
    load_campaign,
)


@dataclass(frozen=True)
class IngestionPreviewSummary:
    """User-facing summary of a parsed-but-not-yet-applied campaign."""

    campaign_id: str
    operator: str
    n_total: int
    profile_keys: tuple[str, ...]
    tier_promotions: tuple[tuple[str, str, str], ...] = field(default_factory=tuple)
    parse_errors: tuple[str, ...] = field(default_factory=tuple)


def _summarise_campaign_for_preview(
    campaign: WetlabCampaign, ingestion_dry_run: IngestionResult,
) -> IngestionPreviewSummary:
    profile_keys = tuple({p.entry.profile_key for p in campaign.data_points})
    return IngestionPreviewSummary(
        campaign_id=campaign.campaign_id,
        operator=campaign.operator,
        n_total=len(campaign.data_points),
        profile_keys=profile_keys,
        tier_promotions=tuple(ingestion_dry_run.tier_promotions),
        parse_errors=tuple(
            f"{pk}: {reason}" for pk, reason in ingestion_dry_run.failures
        ),
    )


def render_wetlab_ingestion_panel(
    *,
    container: Any = None,
    key_prefix: str = "wlab",
) -> Optional[IngestionPreviewSummary]:
    """Render the wet-lab YAML calibration-campaign ingestion panel.

    Returns the preview summary on parse-success, None when no upload
    has happened. The Apply button (when shown) writes the updated
    profiles into ``st.session_state['_cal_store']``-keyed registry.
    """
    target = container if container is not None else st

    target.subheader("Wet-lab calibration ingestion")
    target.caption(
        "Upload a wet-lab campaign (YAML) that maps measurement results "
        "to reagent-profile parameters. Promotes affected outputs to "
        "CALIBRATED_LOCAL tier per the README guardrail. Example "
        "campaigns: `data/wetlab_calibration_examples/`."
    )

    uploaded = target.file_uploader(
        "Upload wet-lab calibration campaign (YAML)",
        type=["yaml", "yml"],
        key=f"{key_prefix}_yaml_upload",
        help=(
            "Required schema: `campaign_id`, `operator`, `entries[]` "
            "(each with `profile_key`, `parameter_name`, "
            "`measured_value`, `target_module`)."
        ),
    )
    if uploaded is None:
        target.info(
            "No campaign uploaded yet. Download an example from "
            "`data/wetlab_calibration_examples/` for the canonical schema."
        )
        return None

    # Parse + dry-run ingestion (no state mutation).
    try:
        text = uploaded.getvalue().decode("utf-8")
    except (UnicodeDecodeError, AttributeError) as exc:
        target.error(f"Could not decode uploaded file as UTF-8: {exc!r}")
        return None
    try:
        campaign = load_campaign(text)
    except Exception as exc:  # YAML scanner errors, ValueError, KeyError, etc.
        target.error(f"Campaign parse failed: {exc}")
        return None

    try:
        dry_run = apply_campaign(campaign, strict=False)
    except (ValueError, TypeError) as exc:
        target.error(f"Ingestion dry-run failed: {exc}")
        return None

    summary = _summarise_campaign_for_preview(campaign, dry_run)

    # Header line.
    cols = target.columns(3)
    cols[0].markdown(f"**Campaign ID**\n\n{summary.campaign_id or '—'}")
    cols[1].markdown(f"**Operator**\n\n{summary.operator or '—'}")
    cols[2].markdown(f"**Data points**\n\n{summary.n_total}")
    cols[2].caption(
        f"applied={dry_run.points_applied}, "
        f"skipped={dry_run.points_skipped}, "
        f"failed={dry_run.points_failed}"
    )

    # Affected profiles.
    if summary.profile_keys:
        with target.expander(
            f"Affected reagent profiles ({len(summary.profile_keys)})"
        ):
            for pk in sorted(summary.profile_keys):
                target.write(f"• `{pk}`")

    # Tier-promotion preview — the headline of the "wet-lab handshake".
    if summary.tier_promotions:
        target.markdown("**Tier-promotion preview** (before → after):")
        for pk, frm, to in summary.tier_promotions:
            target.write(f"• `{pk}` &nbsp; `{frm}` → **`{to}`**")
    else:
        target.caption(
            "No tier promotions in this campaign — measurements either "
            "match existing tier or the registry has no matching profile."
        )

    if summary.parse_errors:
        with target.expander(
            f"Parse errors ({len(summary.parse_errors)})"
        ):
            for err in summary.parse_errors:
                target.warning(err)

    # Apply button — only enabled when at least one promotion exists.
    apply_disabled = (
        len(summary.tier_promotions) == 0
        and dry_run.points_applied == 0
    )
    if target.button(
        "Apply campaign to calibration store",
        key=f"{key_prefix}_apply",
        disabled=apply_disabled,
        type="primary",
    ):
        # Re-run with strict=True for the actual commit.
        try:
            committed = apply_campaign(campaign, strict=True)
        except (ValueError, TypeError) as exc:
            target.error(f"Apply failed: {exc}")
            return summary
        # Persist the updated profile registry overlay on session state.
        existing = st.session_state.get("_wetlab_overlay", {})
        existing.update(committed.profile_updates)
        st.session_state["_wetlab_overlay"] = existing
        st.session_state["_calibration_loaded"] = True
        target.success(
            f"Applied {committed.points_applied} data points; "
            f"{len(committed.tier_promotions)} tier promotions persisted."
        )

    return summary


__all__ = [
    "IngestionPreviewSummary",
    "render_wetlab_ingestion_panel",
]
