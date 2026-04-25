"""Q-012: tests for the Tier-2/3 placeholder UI preview surface.

In v9.2 this surface was used for Tier-2 families that were data-only
in the enum. In v9.3 those Tier-2 families have all been promoted to
selectable Tier-1 status with SEMI_QUANTITATIVE solvers; the preview
has been repurposed for Tier-3 families on the v9.4 roadmap.

This test file verifies the preview surface remains informational-only
(does not enable any family), and that the contents reflect the
current cycle's deferred-roadmap items.
"""

from __future__ import annotations

from dpsim.datatypes import PolymerFamily, is_family_enabled_in_ui
from dpsim.visualization.tabs.m1.family_selector import (
    _FAMILY_DISPLAY,
    _TIER2_PREVIEW_ROWS,
    _enabled_rows,
)


class TestQ012_Tier3Preview:

    def test_preview_rows_present(self):
        """The preview list must be non-empty and well-formed."""
        assert len(_TIER2_PREVIEW_ROWS) >= 6, (
            "Expected at least 6 v9.4 Tier-3 preview entries"
        )
        for entry in _TIER2_PREVIEW_ROWS:
            assert isinstance(entry, tuple) and len(entry) == 2
            name, help_text = entry
            assert name and help_text
            # v9.3 update: preview now lists Tier-3 (v9.4) families
            assert "v9.4" in help_text or "Tier-3" in help_text, (
                f"Preview row for {name!r} should mention v9.4 or Tier-3"
            )

    def test_preview_does_not_include_enabled_families(self):
        """The preview MUST NOT include any UI-enabled family."""
        ui_enabled_display_names = {row[0] for row in _enabled_rows()}
        preview_names = {name for name, _ in _TIER2_PREVIEW_ROWS}
        overlap = ui_enabled_display_names & preview_names
        assert not overlap, (
            f"UI-enabled families incorrectly listed in preview: {overlap}"
        )

    def test_preview_lists_canonical_tier3_concepts(self):
        """v9.3: preview entries name each Tier-3 family concept
        per SA screening report § 6.3."""
        all_text = " ".join(name + " " + help_ for name, help_ in _TIER2_PREVIEW_ROWS).lower()
        for needle in [
            "pectin",
            "gellan",
            "pullulan",
            "starch",
            "borate",
        ]:
            assert needle in all_text, (
                f"Tier-3 preview missing reference to {needle!r}"
            )

    def test_v9_3_promoted_tier2_families_are_now_ui_enabled(self):
        """v9.3: HYALURONATE, KAPPA_CARRAGEENAN, AGAROSE_DEXTRAN,
        AGAROSE_ALGINATE, ALGINATE_CHITOSAN, CHITIN are all now
        UI-enabled (promoted from v9.2 placeholders)."""
        promoted = [
            PolymerFamily.HYALURONATE,
            PolymerFamily.KAPPA_CARRAGEENAN,
            PolymerFamily.AGAROSE_DEXTRAN,
            PolymerFamily.AGAROSE_ALGINATE,
            PolymerFamily.ALGINATE_CHITOSAN,
            PolymerFamily.CHITIN,
        ]
        for fam in promoted:
            assert is_family_enabled_in_ui(fam) is True, (
                f"v9.3 Tier-2 family {fam.value!r} should be UI-enabled "
                f"after v9.3 promotion"
            )

    def test_preview_decoupled_from_enabled_families(self):
        """The display lists must remain disjoint: _FAMILY_DISPLAY
        (selectable) vs _TIER2_PREVIEW_ROWS (informational)."""
        selectable_names = {row[0] for row in _FAMILY_DISPLAY}
        preview_names = {name for name, _ in _TIER2_PREVIEW_ROWS}
        assert selectable_names.isdisjoint(preview_names)
