"""Ion-gelant picker — v0.3.5 UI audit fix.

Surfaces ``ION_GELANT_REGISTRY`` and ``FREESTANDING_ION_GELANTS`` to the
M1 page. The v0.3.3 audit found that 12 of 13 backend ion-gelant entries
had no UI exposure at all — only borax was mentioned via the v9.5
reversibility warning.

This module provides:

* :func:`available_ion_gelants_for_family` — backend lookup that returns
  the set of registry entries (per-family + freestanding) for a given
  :class:`PolymerFamily`. Pure function, no Streamlit dependency, so the
  coverage tests can drive it directly.
* :func:`render_ion_gelant_picker` — Streamlit widget that renders an
  expander under the polymer-family selector showing every available
  ion gelant for the active family, plus a non-biotherapeutic-safe
  warning where appropriate. Returns the user's selection so caller
  formulation pages can wire it through.

Design notes
------------
The legacy alginate formulation page consumes
``dpsim.reagent_library_alginate.GELANTS_ALGINATE`` (its own per-family
registry from v9.0) rather than ``ION_GELANT_REGISTRY``. Both registries
carry the same alginate Ca²⁺ entries; this module's picker reads from
``ION_GELANT_REGISTRY`` so the v9.2-onwards entries (κ-carrageenan / K⁺,
gellan / K⁺ / Ca²⁺ / Al³⁺, pectin / Ca²⁺, hyaluronate / Ca²⁺ cofactor)
are exposed without disturbing the legacy alginate flow.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import streamlit as st

from dpsim.datatypes import PolymerFamily
from dpsim.level2_gelation.ion_registry import (
    FREESTANDING_ION_GELANTS,
    ION_GELANT_REGISTRY,
)


@dataclass(frozen=True)
class IonGelantOption:
    """Display-ready entry for the ion-gelant expander."""

    label: str                 # e.g. "Ca2+ (CaCl2 external) — alginate"
    key: str                   # the (family, ion_string) key or freestanding key
    is_freestanding: bool
    biotherapeutic_safe: bool
    notes: str
    typical_C_bath_mM: float | None
    full_profile: Any          # IonGelantProfile | FreestandingIonGelant


def available_ion_gelants_for_family(
    family: PolymerFamily,
) -> list[IonGelantOption]:
    """Return the ion-gelant options applicable to ``family``.

    The list combines:

    * Every entry from :data:`ION_GELANT_REGISTRY` whose first key
      element matches ``family`` (per-family bound profiles).
    * Every freestanding gelant from :data:`FREESTANDING_ION_GELANTS`
      whose ion is recognised by *any* registry entry for ``family``,
      OR by the family's documented chemistry pattern.

    The freestanding inclusion rule lets the UI show, for example,
    KCl as a free-standing K⁺ source for κ-carrageenan even when the
    bound (KAPPA_CARRAGEENAN, "K+ ...") registry entry is the
    canonical one — the user can see both.

    Returns an empty list for families with no ionic-gelation chemistry
    (e.g. PLGA, agarose-only, dextran).
    """
    out: list[IonGelantOption] = []

    bound_ions: set[str] = set()
    for (fam, ion_key), profile in ION_GELANT_REGISTRY.items():
        if fam.value != family.value:
            continue
        bound_ions.add(profile.ion)
        out.append(IonGelantOption(
            label=f"{ion_key} — {family.value}",
            key=ion_key,
            is_freestanding=False,
            biotherapeutic_safe=profile.biotherapeutic_safe,
            notes=profile.notes,
            typical_C_bath_mM=(
                profile.C_ion_bath if profile.mode == "external_bath"
                else profile.C_ion_source
            ),
            full_profile=profile,
        ))

    if bound_ions:
        for fkey, fprofile in FREESTANDING_ION_GELANTS.items():
            if fprofile.ion not in bound_ions:
                continue
            out.append(IonGelantOption(
                label=f"{fkey} (freestanding {fprofile.ion} source)",
                key=fkey,
                is_freestanding=True,
                biotherapeutic_safe=fprofile.biotherapeutic_safe,
                notes=fprofile.notes,
                typical_C_bath_mM=fprofile.typical_C_bath_mM,
                full_profile=fprofile,
            ))

    return out


def family_has_ion_gelants(family: PolymerFamily) -> bool:
    """``True`` iff at least one ion-gelant profile is registered for the family."""
    return any(
        fam.value == family.value for (fam, _ion) in ION_GELANT_REGISTRY
    )


def render_ion_gelant_picker(
    family: PolymerFamily,
    *,
    expanded: bool = False,
    key_prefix: str = "m1v9",
) -> IonGelantOption | None:
    """Render the ion-gelant selectbox under a Streamlit expander.

    Returns the chosen :class:`IonGelantOption` or ``None`` when the
    family has no ionic-gelation chemistry (in which case the expander
    is not rendered).
    """
    options = available_ion_gelants_for_family(family)
    if not options:
        return None

    with st.expander(
        f"Ion-gelants registered for {family.value}",
        expanded=expanded,
    ):
        st.caption(
            "Selectable per-family + freestanding ion-gelant profiles "
            "from `dpsim.level2_gelation.ion_registry`. v9.0 alginate "
            "page uses its own legacy `GELANTS_ALGINATE` registry; this "
            "expander surfaces the v9.2+ registry entries for parity."
        )
        labels = [opt.label for opt in options]
        sel_idx = st.selectbox(
            "Ion gelant",
            list(range(len(labels))),
            format_func=lambda i: labels[i],
            key=f"{key_prefix}_ion_gelant_{family.value}",
        )
        opt = options[sel_idx]
        if not opt.biotherapeutic_safe:
            st.error(
                f"⚠ {opt.label} is **NOT biotherapeutic-safe**. The "
                f"`biotherapeutic_safe` gate will block this from "
                f"default workflows. Use only for research / non-"
                f"biotherapeutic applications."
            )
        elif opt.is_freestanding:
            st.info(
                f"Freestanding {opt.full_profile.ion} source — "
                f"typical bath ≈ {opt.typical_C_bath_mM:.0f} mM."
            )
        else:
            mode = getattr(opt.full_profile, "mode", "")
            suit = getattr(opt.full_profile, "suitability", None)
            extras = []
            if mode:
                extras.append(f"mode={mode}")
            if suit is not None:
                extras.append(f"suitability={suit}/10")
            if extras:
                st.caption(" | ".join(extras))
        st.markdown(f"**Notes:** {opt.notes}")
        return opt


__all__ = [
    "IonGelantOption",
    "available_ion_gelants_for_family",
    "family_has_ion_gelants",
    "render_ion_gelant_picker",
]
