"""Deterministic process dossier export (B-2d / W-011, v0.6.5).

Reference: docs/update_workplan_2026-05-04.md §4 → B-2d.

Bundles a complete simulation run into a hash-locked, reproducible
dossier suitable for journal supplementary material, IP filings, or
regulatory audit. The dossier is the fifth gate in the validation
release ladder (work plan §5) and the artefact every public claim
about DPSim should be traceable to.

The dossier captures:

  * recipe TOML (raw text, exact bytes — preserves formatting)
  * resolved SimulationParameters
  * M1 / M2 / M3 result contracts (lifecycle outputs)
  * ResultGraph nodes
  * every ModelManifest from the run
  * every CalibrationEntry consumed by the run
  * validation report (BLOCKERs + WARNINGs)
  * git commit short SHA
  * resolved Python package versions
  * smoke-test status
  * recipe hash (sha256 of TOML bytes)
  * calibration-store hash (sha256 of sorted entry tuples)
  * dossier timestamp (UTC ISO 8601)
  * dpsim version

Determinism guarantees:
  * The same recipe + same calibration store + same git commit produce
    the same recipe_hash and calibration_store_hash. The timestamp and
    package_versions are excluded from those hashes (they vary between
    runs and across machines).
  * JSON output is sorted by key at every level so byte-exact comparison
    across runs is meaningful.
"""

from __future__ import annotations

import hashlib
import json
import platform
import subprocess
import sys
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional


# ─── Hash helpers ────────────────────────────────────────────────────────────


def compute_recipe_hash(recipe_toml: str) -> str:
    """SHA-256 of the recipe TOML bytes (UTF-8 encoded)."""
    return hashlib.sha256(recipe_toml.encode("utf-8")).hexdigest()


def compute_calibration_store_hash(entries: list[dict]) -> str:
    """SHA-256 of a sorted, normalised view of the calibration entries.

    Sorting by (profile_key, parameter_name) makes the hash stable across
    different insertion orders. Each entry is serialised as a sorted-key
    JSON string before hashing, so dict ordering inside an entry is also
    irrelevant.
    """
    if not entries:
        return hashlib.sha256(b"").hexdigest()
    sortable = sorted(
        entries,
        key=lambda e: (
            str(e.get("profile_key", "")),
            str(e.get("parameter_name", "")),
            str(e.get("target_module", "")),
        ),
    )
    blob = json.dumps(sortable, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()


def compute_dossier_hash(dossier: ProcessDossier) -> str:
    """SHA-256 of the dossier's content-bearing fields.

    Excludes ``timestamp_utc`` and ``package_versions`` (machine-/time-
    varying) to give a content-addressable identifier suitable for
    deduplication.
    """
    blob = dossier.to_json(include_timestamp=False, include_package_versions=False)
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()


# ─── Environment helpers ────────────────────────────────────────────────────


def get_git_commit_short(repo_root: Optional[Path] = None) -> str:
    """Return the short git SHA of the working tree, or "" on failure.

    Failure modes that yield "": git not on PATH; not a git repo; subprocess
    error; ``repo_root`` does not exist. The dossier accepts an empty
    git_commit (with a corresponding warning in the validation report) so
    a build can still be produced from a non-git checkout.
    """
    cwd = repo_root if repo_root is not None else Path.cwd()
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            cwd=str(cwd), capture_output=True, text=True, timeout=10.0,
        )
        if result.returncode == 0:
            return result.stdout.strip()
    except (FileNotFoundError, subprocess.TimeoutExpired, OSError):
        pass
    return ""


def get_git_dirty(repo_root: Optional[Path] = None) -> bool:
    """True iff the working tree has uncommitted changes (best-effort)."""
    cwd = repo_root if repo_root is not None else Path.cwd()
    try:
        result = subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=str(cwd), capture_output=True, text=True, timeout=10.0,
        )
        if result.returncode == 0:
            return bool(result.stdout.strip())
    except (FileNotFoundError, subprocess.TimeoutExpired, OSError):
        pass
    return False


def get_package_versions(*, packages: Optional[list[str]] = None) -> dict[str, str]:
    """Resolve installed package versions for the listed names.

    If ``packages`` is None, picks DPSim's first-tier dependencies (numpy,
    scipy, pydantic, h5py, matplotlib). The dossier is reproducible only
    insofar as these versions match across runs.
    """
    if packages is None:
        packages = ["numpy", "scipy", "pydantic", "h5py", "matplotlib"]
    versions: dict[str, str] = {}
    for name in packages:
        try:
            from importlib.metadata import version as _ver
            versions[name] = _ver(name)
        except Exception:  # noqa: BLE001 — any resolution failure → "unavailable"
            versions[name] = "unavailable"
    versions["python"] = sys.version.split()[0]
    versions["platform"] = platform.platform()
    return versions


def _dpsim_version() -> str:
    try:
        from dpsim import __version__
        return str(__version__)
    except Exception:  # noqa: BLE001
        return "unknown"


# ─── Dossier dataclass ───────────────────────────────────────────────────────


@dataclass
class ProcessDossier:
    """Immutable-by-convention bundle of one DPSim run's full provenance.

    Every numeric field is a plain Python type so the dossier round-trips
    through ``json.dumps`` / ``json.loads`` without information loss. The
    dataclass is mutable only so that ``build_dossier`` can populate it
    incrementally; consumers should treat instances as read-only.
    """

    # Inputs
    recipe_toml: str = ""
    resolved_parameters: dict = field(default_factory=dict)

    # Lifecycle outputs
    m1_contract: Optional[dict] = None
    m2_contract: Optional[dict] = None
    m3_contract: Optional[dict] = None
    result_graph: list[dict] = field(default_factory=list)
    manifests: list[dict] = field(default_factory=list)

    # Calibration consumed
    calibration_entries: list[dict] = field(default_factory=list)

    # Validation outcomes
    validation_blockers: list[dict] = field(default_factory=list)
    validation_warnings: list[dict] = field(default_factory=list)

    # Reproducibility envelope
    git_commit: str = ""
    git_dirty: bool = False
    package_versions: dict[str, str] = field(default_factory=dict)
    smoke_status: str = "not_run"             # "pass" / "fail" / "not_run"
    dpsim_version: str = ""

    # Hashes (computed once at build_dossier time)
    recipe_hash: str = ""
    calibration_store_hash: str = ""

    # Provenance
    timestamp_utc: str = ""
    notes: str = ""

    def to_dict(
        self,
        *,
        include_timestamp: bool = True,
        include_package_versions: bool = True,
    ) -> dict[str, Any]:
        d = asdict(self)
        if not include_timestamp:
            d.pop("timestamp_utc", None)
        if not include_package_versions:
            d.pop("package_versions", None)
        return d

    def to_json(
        self,
        *,
        include_timestamp: bool = True,
        include_package_versions: bool = True,
    ) -> str:
        """Deterministic JSON serialisation (sort_keys=True, no whitespace)."""
        return json.dumps(
            self.to_dict(
                include_timestamp=include_timestamp,
                include_package_versions=include_package_versions,
            ),
            sort_keys=True,
            separators=(",", ":"),
            default=str,
        )

    def write_json(self, path: Path) -> None:
        """Write the dossier to ``path`` with UTF-8, sorted keys, indented."""
        path.write_text(
            json.dumps(self.to_dict(), sort_keys=True, indent=2, default=str),
            encoding="utf-8",
        )

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> ProcessDossier:
        """Reconstruct a dossier from its dict representation."""
        return cls(
            recipe_toml=str(d.get("recipe_toml", "")),
            resolved_parameters=dict(d.get("resolved_parameters", {})),
            m1_contract=d.get("m1_contract"),
            m2_contract=d.get("m2_contract"),
            m3_contract=d.get("m3_contract"),
            result_graph=list(d.get("result_graph", [])),
            manifests=list(d.get("manifests", [])),
            calibration_entries=list(d.get("calibration_entries", [])),
            validation_blockers=list(d.get("validation_blockers", [])),
            validation_warnings=list(d.get("validation_warnings", [])),
            git_commit=str(d.get("git_commit", "")),
            git_dirty=bool(d.get("git_dirty", False)),
            package_versions=dict(d.get("package_versions", {})),
            smoke_status=str(d.get("smoke_status", "not_run")),
            dpsim_version=str(d.get("dpsim_version", "")),
            recipe_hash=str(d.get("recipe_hash", "")),
            calibration_store_hash=str(d.get("calibration_store_hash", "")),
            timestamp_utc=str(d.get("timestamp_utc", "")),
            notes=str(d.get("notes", "")),
        )

    @classmethod
    def read_json(cls, path: Path) -> ProcessDossier:
        return cls.from_dict(json.loads(path.read_text(encoding="utf-8")))


# ─── Builder ────────────────────────────────────────────────────────────────


def build_dossier(
    *,
    recipe_toml: str,
    resolved_parameters: Optional[dict] = None,
    m1_contract: Optional[dict] = None,
    m2_contract: Optional[dict] = None,
    m3_contract: Optional[dict] = None,
    result_graph: Optional[list[dict]] = None,
    manifests: Optional[list[dict]] = None,
    calibration_entries: Optional[list[dict]] = None,
    validation_blockers: Optional[list[dict]] = None,
    validation_warnings: Optional[list[dict]] = None,
    smoke_status: str = "not_run",
    repo_root: Optional[Path] = None,
    notes: str = "",
) -> ProcessDossier:
    """Assemble a ProcessDossier with computed hashes and environment metadata.

    All inputs except ``recipe_toml`` are optional so the builder can run
    on partial pipelines (e.g. M1-only studies, dry-run validation). Every
    None defaults to an empty container, never a synthetic placeholder.

    The recipe and calibration-store hashes are computed once here and
    stored on the dossier; readers can recompute and compare to detect
    tampering.
    """
    cal = list(calibration_entries) if calibration_entries else []
    return ProcessDossier(
        recipe_toml=recipe_toml,
        resolved_parameters=dict(resolved_parameters or {}),
        m1_contract=m1_contract,
        m2_contract=m2_contract,
        m3_contract=m3_contract,
        result_graph=list(result_graph or []),
        manifests=list(manifests or []),
        calibration_entries=cal,
        validation_blockers=list(validation_blockers or []),
        validation_warnings=list(validation_warnings or []),
        git_commit=get_git_commit_short(repo_root),
        git_dirty=get_git_dirty(repo_root),
        package_versions=get_package_versions(),
        smoke_status=smoke_status,
        dpsim_version=_dpsim_version(),
        recipe_hash=compute_recipe_hash(recipe_toml),
        calibration_store_hash=compute_calibration_store_hash(cal),
        timestamp_utc=datetime.now(timezone.utc).isoformat(timespec="seconds"),
        notes=notes,
    )


__all__ = [
    "ProcessDossier",
    "build_dossier",
    "compute_calibration_store_hash",
    "compute_dossier_hash",
    "compute_recipe_hash",
    "get_git_commit_short",
    "get_git_dirty",
    "get_package_versions",
]
