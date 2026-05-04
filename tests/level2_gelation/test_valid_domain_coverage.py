"""B-1c (W-007) regression: every L2 family ModelManifest must declare a
non-empty valid_domain.

The audit observation: silent extrapolation of L2 pore/structure predictions
outside the calibration window is a primary scientific-validity risk. The
machine-readable valid_domain on each ModelManifest is the contract that
lets the render path (B-1b decision_grade gate) downgrade outputs that
fall outside the envelope.

Strategy: AST-scan every `level2_gelation/*.py` source file for
`ModelManifest(...)` constructions and assert that each construction either
(a) sets a non-empty literal `valid_domain={...}` keyword, or (b) is
unambiguously a degenerate / UNSUPPORTED-tier short-circuit (the manifest
emitted when input is zero / unphysical and the solver returns immediately).

The (b) carve-out preserves the v0.6.4 invariant that an UNSUPPORTED model
correctly publishes an empty domain; non-UNSUPPORTED tiers must populate.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

L2_DIR = Path(__file__).resolve().parents[2] / "src" / "dpsim" / "level2_gelation"


def _all_l2_modules() -> list[Path]:
    return sorted(p for p in L2_DIR.glob("*.py") if p.name != "__init__.py")


def _manifest_constructions(module_path: Path) -> list[tuple[ast.Call, ast.Module]]:
    """Yield every ast.Call node whose func is `ModelManifest`."""
    tree = ast.parse(module_path.read_text(encoding="utf-8"))
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            func = node.func
            if isinstance(func, ast.Name) and func.id == "ModelManifest":
                out.append((node, tree))
            elif isinstance(func, ast.Attribute) and func.attr == "ModelManifest":
                out.append((node, tree))
    return out


def _kwarg(call: ast.Call, name: str) -> ast.expr | None:
    for kw in call.keywords:
        if kw.arg == name:
            return kw.value
    return None


def _is_unsupported_tier(call: ast.Call) -> bool:
    """True iff evidence_tier=ModelEvidenceTier.UNSUPPORTED is the literal."""
    tier = _kwarg(call, "evidence_tier")
    if tier is None:
        return False
    if isinstance(tier, ast.Attribute) and tier.attr == "UNSUPPORTED":
        return True
    return False


def _has_nonempty_valid_domain(call: ast.Call, module: ast.Module) -> bool:
    """True iff valid_domain is set to a non-empty literal dict OR a Name
    that the surrounding code populated before the call.

    For B-1c we accept either:
      * `valid_domain={...}` literal with at least one key
      * `valid_domain=<identifier>` where the identifier is built from a
        non-empty inherited dict (tier2/tier3/v9_5 helpers — they set
        `inherited_domain[...]` then pass it as `valid_domain`).
    """
    vd = _kwarg(call, "valid_domain")
    if vd is None:
        return False
    if isinstance(vd, ast.Dict):
        return len(vd.keys) > 0
    if isinstance(vd, ast.Name):
        # Helper pattern: `valid_domain=inherited_domain` after dict ops.
        # Search for `setdefault` or `[...] =` operations on this name in
        # the same module body.
        target = vd.id
        for node in ast.walk(module):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
                if (
                    isinstance(node.func.value, ast.Name)
                    and node.func.value.id == target
                    and node.func.attr in {"setdefault", "update", "__setitem__"}
                ):
                    return True
            if isinstance(node, ast.Subscript) and isinstance(node.value, ast.Name):
                if node.value.id == target:
                    return True
        return False
    return False


@pytest.mark.parametrize(
    "module_path",
    _all_l2_modules(),
    ids=lambda p: p.stem,
)
def test_every_l2_manifest_declares_valid_domain(module_path):
    """Every L2 ModelManifest must declare a non-empty valid_domain unless
    its evidence_tier is UNSUPPORTED (degenerate / zero-input short-circuit)."""
    constructions = _manifest_constructions(module_path)
    if not constructions:
        pytest.skip(f"{module_path.name} has no ModelManifest constructions")

    failures: list[str] = []
    for call, module in constructions:
        if _is_unsupported_tier(call):
            # UNSUPPORTED tier indicates the solver short-circuited; an
            # empty valid_domain is semantically correct.
            continue
        if not _has_nonempty_valid_domain(call, module):
            line = call.lineno
            model_name_kw = _kwarg(call, "model_name")
            label = (
                ast.literal_eval(model_name_kw)
                if isinstance(model_name_kw, ast.Constant)
                else f"<line {line}>"
            )
            failures.append(f"{module_path.name}:{line} {label}")

    assert not failures, (
        "L2 manifests missing non-empty valid_domain (B-1c / W-007):\n  "
        + "\n  ".join(failures)
    )
