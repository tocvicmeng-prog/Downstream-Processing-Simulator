from __future__ import annotations

from dpsim.core.process_recipe import default_affinity_media_recipe
from dpsim.visualization.provenance import (
    PROVENANCE_STATE_KEY,
    build_result_provenance,
    get_result_provenance,
    provenance_summary_html,
    recipe_fingerprint,
    store_result_provenance,
    with_current_recipe_staleness,
)


def test_recipe_fingerprint_changes_when_recipe_changes():
    recipe = default_affinity_media_recipe()
    before = recipe_fingerprint(recipe)

    recipe.owner = "changed-owner"

    assert recipe_fingerprint(recipe) != before


def test_provenance_round_trips_through_session_mapping():
    recipe = default_affinity_media_recipe()
    store = {}
    provenance = build_result_provenance(
        source="lifecycle",
        recipe=recipe,
        result_id="run-42",
        scientific_mode="hybrid",
        evidence_tier="semi_quantitative",
    )

    store_result_provenance(store, "lifecycle_result", provenance)
    loaded = get_result_provenance(store, "lifecycle_result")

    assert PROVENANCE_STATE_KEY in store
    assert loaded == provenance


def test_staleness_compares_against_current_recipe():
    recipe = default_affinity_media_recipe()
    provenance = build_result_provenance(source="direct_m3", recipe=recipe)

    assert with_current_recipe_staleness(provenance, recipe).stale is False

    changed = default_affinity_media_recipe()
    changed.owner = "new-owner"
    stale = with_current_recipe_staleness(provenance, changed)

    assert stale.stale is True
    assert stale.stale_reasons


def test_provenance_html_escapes_values():
    recipe = default_affinity_media_recipe()
    provenance = build_result_provenance(
        source="<script>",
        recipe=recipe,
        scientific_mode="<mode>",
        evidence_tier="<tier>",
    )

    html = provenance_summary_html(provenance)

    assert "<script>" not in html
    assert "&lt;script&gt;" in html
