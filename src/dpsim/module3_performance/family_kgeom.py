"""Per-family K_geom registry for u_crit pressure-envelope computation.

B-2f / W-020 + W-026: Δ1 + Δ7 from the v0.7.0 M3 back-pressure work plan
(``docs/update_workplan_2026-05-10_m3_pressure.md``).

The operational pressure limit ΔP_max for a packed chromatography bed
is governed by the bed-compression u_crit knee, NOT by bead bursting:

    u_crit ≈ K_geom_family · G_DN · d_p² / (μ · L)

where K_geom_family is a dimensionless prefactor that depends on the
bead packing arrangement and the polymer family's mechanical response
(stiffness vs creep behaviour). The v0.6.6 code anchored ΔP_max to
``safety × E_star`` (the bursting modulus, scientifically wrong by
5–50× factor for soft chromatography media); B-2f replaces that anchor
with this u_crit formulation.

Per the validation release-gate ladder (work plan §4.2 gate 7), each
family's K_geom carries a literature-anchored default at evidence tier
``SEMI_QUANTITATIVE``. Promotion to ``CALIBRATED_LOCAL`` requires either
a manufacturer pressure-flow curve OR local wet-lab pressure-flow data
for the specific resin / column / buffer system.

Family-First contract (CLAUDE.md v9.0)
--------------------------------------
The registry is keyed by ``PolymerFamily.value`` (the string), not by
the enum member. Streamlit reload aliasing mints a fresh
``PolymerFamily`` class on every rerun; comparing by ``.value`` is the
only reliable lookup pattern.

K_geom anchor rationale
-----------------------
The literature span for K_geom across chromatography polymers is
roughly 1×10⁻³ to 2×10⁻² (sci-advisor delivery 2026-05-10 §B). Per-
family ordering anchors:

* CELLULOSE — rigid fibrous backbone; published u_crit up to ~1000 cm/h
  for Cellufine / Capto S class media. K_geom = 2×10⁻² (highest).
* PLGA — glassy at T < T_g (~37–55 °C depending on lactide-glycolide
  ratio); rubbery above T_g. v0.7 anchors at the glassy state.
  K_geom = 1×10⁻². T_g-dependence flagged as future scope.
* AGAROSE_CHITOSAN — interpenetrating network; stiffer-per-Pa than pure
  agarose at same nominal G_DN. K_geom = 8×10⁻³ (above pure agarose).
* AGAROSE — Sepharose-class 4–6 % CL at canonical 4 °C: published max
  linear velocity 300–500 cm/h. K_geom = 5×10⁻³ (anchor).
* ALGINATE — ionically crosslinked; more compliant under axial drag,
  Ca²⁺-concentration-dependent; G_DN drops sharply on EDTA exposure.
  K_geom = 3×10⁻³ (below agarose).

Other PolymerFamily values (CHITOSAN, DEXTRAN, HYALURONATE, etc.)
fall back to a conservative default with ``QUALITATIVE_TREND`` tier
until per-family calibration data lands. The registry is closed-set;
``lookup_family_kgeom`` raises ``KeyError`` for unregistered families
to force the developer to add a row before shipping.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from dpsim.datatypes import ModelEvidenceTier, PolymerFamily


# ─── Per-family value object ────────────────────────────────────────────────


@dataclass(frozen=True)
class FamilyKGeom:
    """Per-family u_crit prefactor + valid_domain envelope.

    Attributes
    ----------
    family_value :
        ``PolymerFamily.value`` for this family (string). Compared by
        value per the v9.0 Family-First UI contract; never compared by
        identity.
    K_geom :
        Dimensionless u_crit prefactor in u_crit = K_geom · G_DN · d_p² / (μ · L).
        Range: roughly 1e-3 to 2e-2 across chromatography polymers.
    valid_domain :
        Mapping from parameter name to (lower, upper) bounds. Mirrors
        the L2 family ``valid_domain`` shape (B-1c precedent at
        ``level2_gelation/ionic_ca.py:249``). The keys checked by
        ``compute_pressure_envelope`` are ``bead_d32_m``, ``bed_height_m``,
        ``T_C``, ``mu_pa_s``, ``G_DN_pa``.
    base_tier :
        Evidence tier when the user is *inside* the valid_domain and no
        manufacturer pressure-flow curve is supplied. Always
        ``SEMI_QUANTITATIVE`` for the v0.7 default-anchor families;
        ``QUALITATIVE_TREND`` for fallback families.
    literature_anchor :
        Citation key (e.g. "Stickel2001", "manufacturer_GE_2009"). Free-
        text; for traceability in the dossier export.
    notes :
        Human-readable provenance string.
    """

    family_value: str
    K_geom: float
    valid_domain: dict[str, tuple[float, float]] = field(default_factory=dict)
    base_tier: ModelEvidenceTier = ModelEvidenceTier.SEMI_QUANTITATIVE
    literature_anchor: str = ""
    notes: str = ""


# ─── Registry ────────────────────────────────────────────────────────────────


# Default valid_domain for the canonical chromatography operating window.
# Individual families may tighten or widen each range; bounds outside
# these ranges trigger tier downgrade (one step) per architect §4 seam #7.
_DEFAULT_VALID_DOMAIN: dict[str, tuple[float, float]] = {
    "bead_d32_m": (40e-6, 200e-6),       # 40–200 µm covers analytical → preparative
    "bed_height_m": (0.05, 0.50),        # 5–50 cm bed
    "T_C": (4.0, 30.0),                  # cold room → warm process
    "mu_pa_s": (0.8e-3, 5e-3),           # water-like → moderate viscosity
    "G_DN_pa": (1e3, 1e6),               # soft hydrogel → rigid composite
}


FAMILY_KGEOM_REGISTRY: dict[str, FamilyKGeom] = {
    PolymerFamily.AGAROSE.value: FamilyKGeom(
        family_value=PolymerFamily.AGAROSE.value,
        K_geom=5e-3,
        valid_domain=dict(_DEFAULT_VALID_DOMAIN),
        base_tier=ModelEvidenceTier.SEMI_QUANTITATIVE,
        literature_anchor="Stickel2001",
        notes=(
            "Sepharose-class agarose 4–6% CL. Published max linear velocity "
            "300–500 cm/h at 4 °C with water-like buffers. Anchor calibrated "
            "to the GE Healthcare pressure-flow curve at L = 10 cm."
        ),
    ),
    PolymerFamily.AGAROSE_CHITOSAN.value: FamilyKGeom(
        family_value=PolymerFamily.AGAROSE_CHITOSAN.value,
        K_geom=8e-3,
        valid_domain=dict(_DEFAULT_VALID_DOMAIN),
        base_tier=ModelEvidenceTier.SEMI_QUANTITATIVE,
        literature_anchor="DPSim_default_recipe",
        notes=(
            "Interpenetrating-network composite (DPSim default first-run "
            "recipe). Stiffer per Pa than pure agarose at same nominal G_DN; "
            "tolerates higher u_crit. Wet-lab calibration pending."
        ),
    ),
    PolymerFamily.CELLULOSE.value: FamilyKGeom(
        family_value=PolymerFamily.CELLULOSE.value,
        K_geom=2e-2,
        valid_domain=dict(_DEFAULT_VALID_DOMAIN),
        base_tier=ModelEvidenceTier.SEMI_QUANTITATIVE,
        literature_anchor="Cellufine_CaptoS_appnote",
        notes=(
            "Rigid fibrous backbone. Cellufine / Capto S-class media run "
            "at u_crit up to ~1000 cm/h. Highest K_geom of the v0.7 "
            "default-anchor families."
        ),
    ),
    PolymerFamily.PLGA.value: FamilyKGeom(
        family_value=PolymerFamily.PLGA.value,
        K_geom=1e-2,
        valid_domain={
            **_DEFAULT_VALID_DOMAIN,
            "T_C": (4.0, 25.0),  # T_g-aware: keep below T_g_glassy_min for v0.7
        },
        base_tier=ModelEvidenceTier.SEMI_QUANTITATIVE,
        literature_anchor="PLGA_glassy_state_anchor",
        notes=(
            "Anchor at glassy-state mechanical response (T < T_g, typically "
            "T_g ≈ 37–55 °C depending on lactide-glycolide ratio). "
            "Rubbery-state behaviour above T_g is future scope; the "
            "valid_domain T_C upper bound is tightened to 25 °C in v0.7."
        ),
    ),
    PolymerFamily.ALGINATE.value: FamilyKGeom(
        family_value=PolymerFamily.ALGINATE.value,
        K_geom=3e-3,
        valid_domain=dict(_DEFAULT_VALID_DOMAIN),
        base_tier=ModelEvidenceTier.SEMI_QUANTITATIVE,
        literature_anchor="Stickel2001",
        notes=(
            "Ionically crosslinked; more compliant under axial drag than "
            "covalently-crosslinked agarose. Ca²⁺-concentration-dependent: "
            "G_DN drops sharply on EDTA / chelator exposure → u_crit drops "
            "with it. Lowest K_geom of the v0.7 default-anchor families."
        ),
    ),
}


# Conservative fallback for PolymerFamily values not yet calibrated.
# Carries QUALITATIVE_TREND tier so any prediction using the fallback
# is rendered as INTERVAL/RANK_BAND, never NUMBER.
_FALLBACK_KGEOM: FamilyKGeom = FamilyKGeom(
    family_value="__fallback__",
    K_geom=2e-3,  # conservative low-end; under-predicts u_crit (safer)
    valid_domain=dict(_DEFAULT_VALID_DOMAIN),
    base_tier=ModelEvidenceTier.QUALITATIVE_TREND,
    literature_anchor="conservative_fallback",
    notes=(
        "Fallback for unregistered PolymerFamily values. Conservative low-"
        "end K_geom under-predicts u_crit, which is the safe bias for an "
        "operational limit. Tier QUALITATIVE_TREND demotes any rendering "
        "to INTERVAL or RANK_BAND."
    ),
)


# ─── Public API ──────────────────────────────────────────────────────────────


def lookup_family_kgeom(
    family: PolymerFamily,
    *,
    use_fallback: bool = True,
) -> FamilyKGeom:
    """Look up the K_geom entry for a PolymerFamily.

    Compares by ``.value`` per the v9.0 Family-First UI contract — never
    by identity, never by membership equality on the enum object itself.

    Parameters
    ----------
    family :
        The PolymerFamily to look up.
    use_fallback :
        When ``True`` (default), unregistered families return a
        conservative ``_FALLBACK_KGEOM`` entry at QUALITATIVE_TREND tier.
        When ``False``, raises ``KeyError`` instead. Set to ``False`` in
        contexts where silently using the fallback would mask a missing
        calibration (e.g., release-gate checks).

    Returns
    -------
    FamilyKGeom
        The registry entry for the family, or the fallback when
        ``use_fallback=True`` and the family is not registered.

    Raises
    ------
    KeyError
        If the family is not registered and ``use_fallback=False``.
    """
    family_value = family.value
    entry = FAMILY_KGEOM_REGISTRY.get(family_value)
    if entry is not None:
        return entry
    if use_fallback:
        return _FALLBACK_KGEOM
    raise KeyError(
        f"No K_geom registered for PolymerFamily {family_value!r}. "
        "Add a row to FAMILY_KGEOM_REGISTRY in family_kgeom.py, or call "
        "with use_fallback=True to accept the conservative fallback."
    )


def is_family_registered(family: PolymerFamily) -> bool:
    """Return whether ``family`` has a calibrated K_geom entry.

    ``False`` means the fallback (conservative low-end + QUALITATIVE_TREND
    tier) would be used; ``True`` means a per-family default-anchor entry
    is in the registry.
    """
    return family.value in FAMILY_KGEOM_REGISTRY


def registered_families() -> tuple[str, ...]:
    """Return the tuple of registered PolymerFamily values, sorted."""
    return tuple(sorted(FAMILY_KGEOM_REGISTRY.keys()))


# ─── valid_domain checking ───────────────────────────────────────────────────


def check_valid_domain(
    family_kgeom: FamilyKGeom,
    *,
    bead_d32_m: float,
    bed_height_m: float,
    T_C: float,
    mu_pa_s: float,
    G_DN_pa: float,
) -> tuple[str, ...]:
    """Walk a family's valid_domain and return violations.

    Each value is compared against the family's domain bounds; a value
    outside [lo, hi] produces a human-readable violation string. The
    returned tuple is empty when all values are inside the domain.

    The downstream ``compute_pressure_envelope`` (B-2f) reads this list
    and demotes ``decision_tier`` by one step per non-empty violations
    list (one demotion total, regardless of how many bounds were broken).

    Parameters
    ----------
    family_kgeom :
        The registry entry to check against (typically from
        ``lookup_family_kgeom``).
    bead_d32_m, bed_height_m, T_C, mu_pa_s, G_DN_pa :
        The resolved values to check. All in SI except T_C (°C).

    Returns
    -------
    tuple[str, ...]
        Violation strings. Empty when in-domain.
    """
    violations: list[str] = []
    inputs = {
        "bead_d32_m": bead_d32_m,
        "bed_height_m": bed_height_m,
        "T_C": T_C,
        "mu_pa_s": mu_pa_s,
        "G_DN_pa": G_DN_pa,
    }
    for key, value in inputs.items():
        bounds = family_kgeom.valid_domain.get(key)
        if bounds is None:
            continue
        lo, hi = bounds
        if value < lo or value > hi:
            violations.append(
                f"{key}={value:.4g} outside [{lo:.4g}, {hi:.4g}] for "
                f"family {family_kgeom.family_value!r}"
            )
    return tuple(violations)
