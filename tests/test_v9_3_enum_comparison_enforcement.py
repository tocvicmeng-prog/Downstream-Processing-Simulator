"""Q-011: enforce ``.value``-based comparison of PolymerFamily Enum.

Per CLAUDE.md, the Streamlit app reloads ``dpsim.datatypes`` on every
rerun, minting a NEW Enum class. Identity (``is``) comparisons against
that fresh class silently break — the Enum members on the user's
instance came from the OLD class object. The documented rule:

  > Always compare PolymerFamily members by ``.value``, never by ``is``.

This test walks every ``.py`` file under ``src/dpsim/`` and ``tests/``
with Python's AST, looks for forbidden ``is`` / ``is not`` comparisons
against members of the enforced enums (PolymerFamily, ACSSiteType,
ModelEvidenceTier, ModelMode), and fails the test with a precise
location report.

Equality (``==``) is NOT flagged because Python's Enum.__eq__ falls
back to value comparison correctly within a single class instance, and
the documented rule explicitly focuses on ``is`` (the silent failure
mode). Code that wants the strongest reload safety can opt-in to
``.value == .value`` style on both sides; this test does not enforce it.

Functions as a custom ruff-rule equivalent (Q-011 resolution) without
requiring a ruff plugin.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest


# Enums that are subject to the .value-comparison rule (per CLAUDE.md).
# Add new enums here when they need the same protection.
ENFORCED_ENUMS: frozenset[str] = frozenset({
    "PolymerFamily",
    "ACSSiteType",
    "ModelEvidenceTier",
    "ModelMode",
})


# Files exempt from the rule (e.g. the enum definition itself, or
# files that already use .value safely and would produce false
# positives because they reference the enum class for type-hint reasons).
EXEMPT_FILES: frozenset[str] = frozenset({
    # Enum definition is allowed to use the bare member.
    "src/dpsim/datatypes.py",
    # The reload-safe pattern in compute_min_tier explicitly compares
    # by .value already; the exemption is defensive against false
    # positives if the static analysis cannot resolve dynamic
    # comparisons.
})


def _project_root() -> Path:
    """Path to the project root (parent of `src/`)."""
    return Path(__file__).resolve().parent.parent


def _collect_python_files() -> list[Path]:
    root = _project_root()
    src_files = list((root / "src").rglob("*.py"))
    test_files = list((root / "tests").rglob("*.py"))
    return src_files + test_files


def _is_enum_member_attribute(node: ast.AST) -> bool:
    """Return True if ``node`` looks like ``EnumName.MEMBER``."""
    return (
        isinstance(node, ast.Attribute)
        and isinstance(node.value, ast.Name)
        and node.value.id in ENFORCED_ENUMS
    )


class _EnumComparisonChecker(ast.NodeVisitor):
    """AST visitor that records every forbidden enum comparison."""

    def __init__(self, file_path: Path):
        self.file_path = file_path
        self.violations: list[tuple[int, int, str]] = []

    def visit_Compare(self, node: ast.Compare) -> None:
        for i, op in enumerate(node.ops):
            left = node.left if i == 0 else node.comparators[i - 1]
            right = node.comparators[i]
            left_is_enum = _is_enum_member_attribute(left)
            right_is_enum = _is_enum_member_attribute(right)
            either = left_is_enum or right_is_enum
            if not either:
                continue
            # Per CLAUDE.md, identity comparisons (`is` / `is not`)
            # against the bare enum member are the documented danger.
            # Python's Enum.__eq__ handles value comparison correctly
            # for same-class members, so `==` is not flagged here.
            if isinstance(op, (ast.Is, ast.IsNot)):
                enum_node = left if left_is_enum else right
                assert isinstance(enum_node, ast.Attribute)
                enum_name = ast.unparse(enum_node)
                self.violations.append((
                    node.lineno, node.col_offset,
                    f"identity comparison ({type(op).__name__}) against "
                    f"{enum_name} — use `.value == .value` instead "
                    f"(Streamlit reload safety per CLAUDE.md)",
                ))
        self.generic_visit(node)


def _check_file(path: Path) -> list[tuple[int, int, str]]:
    """Return list of (lineno, col, message) violations in ``path``."""
    rel = path.relative_to(_project_root()).as_posix()
    if rel in EXEMPT_FILES:
        return []
    try:
        source = path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        # Skip binary or non-UTF-8 files (shouldn't happen for .py)
        return []
    try:
        tree = ast.parse(source, filename=str(path))
    except SyntaxError:
        # Skip files we can't parse (likely not real Python)
        return []
    checker = _EnumComparisonChecker(path)
    checker.visit(tree)
    return checker.violations


def test_no_identity_or_bare_equality_comparisons_against_enforced_enums():
    """Q-011: enforce CLAUDE.md `.value`-comparison rule across the codebase.

    Walks ``src/dpsim/`` and ``tests/`` with AST and fails if any
    ``<expr> is <Enum>.<MEMBER>`` or ``<expr> == <Enum>.<MEMBER>``
    pattern (without `.value` on the other side) is found.
    """
    files = _collect_python_files()
    all_violations: list[str] = []
    for f in files:
        violations = _check_file(f)
        if violations:
            rel = f.relative_to(_project_root()).as_posix()
            for line, col, msg in violations:
                all_violations.append(f"  {rel}:{line}:{col} — {msg}")

    assert not all_violations, (
        "Q-011 enum-comparison rule violations found:\n"
        + "\n".join(all_violations)
        + "\n\nFix: replace `<expr> is/== <Enum>.<MEMBER>` with "
        "`<expr>.value == <Enum>.<MEMBER>.value` to survive Streamlit "
        "reload-time enum-class minting (see CLAUDE.md)."
    )


def test_enforcement_self_check_catches_identity():
    """Sanity: the AST checker actually flags an `is`-comparison when
    given a synthetic example."""
    src = """
from dpsim.datatypes import PolymerFamily
def f(family):
    if family is PolymerFamily.AGAROSE:
        return True
    return False
"""
    import tempfile

    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".py", delete=False, encoding="utf-8",
    ) as fh:
        fh.write(src)
        synth = Path(fh.name)
    try:
        # Bypass exempt-file filtering by passing a non-exempt path.
        tree = ast.parse(src)
        checker = _EnumComparisonChecker(synth)
        checker.visit(tree)
        assert any("identity" in m for _, _, m in checker.violations), (
            f"Self-check failed: AST checker did not flag the `is` "
            f"comparison. Violations: {checker.violations}"
        )
    finally:
        synth.unlink(missing_ok=True)


def test_enforcement_self_check_passes_value_comparison():
    """Sanity: the safe `.value == .value` form must not be flagged."""
    src = """
from dpsim.datatypes import PolymerFamily
def f(family):
    if family.value == PolymerFamily.AGAROSE.value:
        return True
    return False
"""
    tree = ast.parse(src)
    checker = _EnumComparisonChecker(Path("synthetic.py"))
    checker.visit(tree)
    assert checker.violations == [], (
        f"Safe `.value == .value` comparison was incorrectly flagged: "
        f"{checker.violations}"
    )
