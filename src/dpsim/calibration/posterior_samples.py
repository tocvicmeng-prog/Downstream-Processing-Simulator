"""Posterior-sample container for the v0.3.0 MC-LRM uncertainty driver.

G1 module of the P5++ initiative (DEVORCH joint plan § 12). Provides a typed
``PosteriorSamples`` container that bridges the existing ``CalibrationEntry``
schema (and the v0.2.0 wet-lab ingestion path) to G2's per-sample LRM solves.

Two sampling paths are exposed via :meth:`PosteriorSamples.draw`:

* **LHS** (Latin Hypercube) — default for marginal-only posteriors. Uses
  ``scipy.stats.qmc.LatinHypercube`` followed by an inverse-CDF transform of
  the unit-cube design through ``scipy.stats.norm(mean, std)``. Independent
  marginals are assumed.
* **multivariate_normal** — used when a full covariance Σ is attached.
  Delegates to ``np.random.default_rng(seed).multivariate_normal``.

The ``method="auto"`` rule (joint plan § 12.3) picks ``multivariate_normal``
when :pyattr:`PosteriorSamples.has_covariance` is true and ``lhs`` otherwise.
A WARNING log is emitted when auto falls back to LHS so that users notice
they are getting a marginal-only draw.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Literal

import numpy as np
from scipy import stats
from scipy.stats import qmc

from .calibration_data import CalibrationEntry

if TYPE_CHECKING:
    from .calibration_store import CalibrationStore

logger = logging.getLogger("dpsim.calibration.posterior_samples")

DrawMethod = Literal["lhs", "multivariate_normal", "auto"]


@dataclass
class PosteriorSamples:
    """Typed posterior-samples container for forward MC uncertainty propagation.

    Attributes
    ----------
    parameter_names : tuple[str, ...]
        Names of the parameters in draw order (e.g.
        ``("q_max", "K_affinity", "pH_transition")``).
    means : np.ndarray
        Marginal posterior means, shape ``(n_params,)``. Units carried by
        ``source_calibration_entries`` rather than this object.
    stds : np.ndarray
        Marginal posterior standard deviations, shape ``(n_params,)``.
        Must be non-negative.
    covariance : np.ndarray | None
        Full posterior covariance matrix, shape ``(n_params, n_params)``, or
        ``None`` for marginal-only mode. Must be symmetric positive
        semi-definite when supplied.
    source_calibration_entries : list[CalibrationEntry]
        Provenance — the calibration entries from which the posterior was
        derived. Empty list permitted for synthetic constructions.
    """

    parameter_names: tuple[str, ...]
    means: np.ndarray
    stds: np.ndarray
    covariance: np.ndarray | None = None
    source_calibration_entries: list[CalibrationEntry] = field(default_factory=list)

    def __post_init__(self) -> None:
        if not self.parameter_names:
            raise ValueError("parameter_names must be non-empty")
        if len(set(self.parameter_names)) != len(self.parameter_names):
            raise ValueError(
                f"parameter_names must be unique, got {self.parameter_names!r}"
            )
        if not isinstance(self.parameter_names, tuple):
            self.parameter_names = tuple(self.parameter_names)

        n = len(self.parameter_names)

        self.means = np.asarray(self.means, dtype=float)
        if self.means.shape != (n,):
            raise ValueError(
                f"means shape {self.means.shape} != expected ({n},)"
            )
        if not np.all(np.isfinite(self.means)):
            raise ValueError("means must be finite")

        self.stds = np.asarray(self.stds, dtype=float)
        if self.stds.shape != (n,):
            raise ValueError(
                f"stds shape {self.stds.shape} != expected ({n},)"
            )
        if np.any(self.stds < 0):
            raise ValueError(
                f"stds must be non-negative, got {self.stds.tolist()}"
            )
        if not np.all(np.isfinite(self.stds)):
            raise ValueError("stds must be finite")

        if self.covariance is not None:
            cov = np.asarray(self.covariance, dtype=float)
            if cov.shape != (n, n):
                raise ValueError(
                    f"covariance shape {cov.shape} != expected ({n}, {n})"
                )
            if not np.allclose(cov, cov.T, atol=1e-10):
                raise ValueError("covariance must be symmetric")
            try:
                np.linalg.cholesky(cov + 1e-12 * np.eye(n))
            except np.linalg.LinAlgError as exc:
                raise ValueError(
                    "covariance must be positive semi-definite"
                ) from exc
            self.covariance = cov

    @property
    def has_covariance(self) -> bool:
        """True iff a full covariance matrix is attached (not marginal-only)."""
        return self.covariance is not None

    @property
    def n_params(self) -> int:
        return len(self.parameter_names)

    def draw(
        self,
        n: int,
        seed: int = 0,
        method: DrawMethod = "auto",
    ) -> np.ndarray:
        """Draw ``n`` samples from the posterior.

        Parameters
        ----------
        n : int
            Number of samples to draw. Must be > 0.
        seed : int
            Seed for the underlying RNG; identical seeds yield identical draws.
        method : {"lhs", "multivariate_normal", "auto"}
            Sampling method. ``"auto"`` picks ``multivariate_normal`` when a
            covariance is attached and ``"lhs"`` otherwise.

        Returns
        -------
        np.ndarray
            Draws of shape ``(n, n_params)``.
        """
        if n <= 0:
            raise ValueError(f"n must be > 0, got {n}")

        resolved = self._resolve_method(method)

        if resolved == "lhs":
            sampler = qmc.LatinHypercube(d=self.n_params, seed=seed)
            u = sampler.random(n)
            return stats.norm.ppf(u, loc=self.means, scale=self.stds)

        if resolved == "multivariate_normal":
            cov = self.covariance
            if cov is None:
                cov = np.diag(self.stds**2)
            rng = np.random.default_rng(seed)
            return rng.multivariate_normal(self.means, cov, size=n)

        raise ValueError(f"Unknown method {method!r}")

    def _resolve_method(self, method: DrawMethod) -> str:
        if method == "auto":
            if self.has_covariance:
                return "multivariate_normal"
            logger.debug(
                "draw(method='auto') falling back to LHS — no covariance attached"
            )
            return "lhs"
        if method in ("lhs", "multivariate_normal"):
            return method
        raise ValueError(
            f"Unknown method {method!r}; expected one of "
            "'lhs', 'multivariate_normal', 'auto'"
        )

    def to_dict(self) -> dict[str, Any]:
        """Serialise to a JSON-compatible dict."""
        return {
            "parameter_names": list(self.parameter_names),
            "means": self.means.tolist(),
            "stds": self.stds.tolist(),
            "covariance": (
                self.covariance.tolist() if self.covariance is not None else None
            ),
            "source_calibration_entries": [
                entry.to_dict() for entry in self.source_calibration_entries
            ],
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> PosteriorSamples:
        """Deserialise from a dict produced by :meth:`to_dict`."""
        cov = d.get("covariance")
        return cls(
            parameter_names=tuple(d["parameter_names"]),
            means=np.asarray(d["means"], dtype=float),
            stds=np.asarray(d["stds"], dtype=float),
            covariance=(np.asarray(cov, dtype=float) if cov is not None else None),
            source_calibration_entries=[
                CalibrationEntry.from_dict(e)
                for e in d.get("source_calibration_entries", [])
            ],
        )

    @classmethod
    def from_marginals(
        cls,
        parameter_names: tuple[str, ...],
        means: np.ndarray,
        stds: np.ndarray,
        source_entries: list[CalibrationEntry] | None = None,
    ) -> PosteriorSamples:
        """Construct from independent marginal means/stds (no covariance)."""
        return cls(
            parameter_names=tuple(parameter_names),
            means=np.asarray(means, dtype=float),
            stds=np.asarray(stds, dtype=float),
            covariance=None,
            source_calibration_entries=list(source_entries or []),
        )

    @classmethod
    def from_covariance(
        cls,
        parameter_names: tuple[str, ...],
        means: np.ndarray,
        covariance: np.ndarray,
        source_entries: list[CalibrationEntry] | None = None,
    ) -> PosteriorSamples:
        """Construct from a full covariance matrix.

        Marginal stds are derived from the diagonal of ``covariance``.
        """
        cov = np.asarray(covariance, dtype=float)
        stds = np.sqrt(np.diag(cov))
        return cls(
            parameter_names=tuple(parameter_names),
            means=np.asarray(means, dtype=float),
            stds=stds,
            covariance=cov,
            source_calibration_entries=list(source_entries or []),
        )

    @classmethod
    def from_calibration_store(
        cls,
        store: CalibrationStore,
        parameter_names: tuple[str, ...],
    ) -> PosteriorSamples:
        """Build a posterior from a :class:`CalibrationStore`.

        For each name in ``parameter_names``, finds an entry in the store
        whose ``parameter_name`` matches and reads ``measured_value`` as the
        posterior mean and ``posterior_uncertainty`` as the marginal std.

        A covariance is attached when *every* matched entry carries a
        ``valid_domain["covariance_row"]`` field listing the off-diagonal
        terms keyed by parameter name; this matches the schema produced by
        the v0.3.1 Bayesian-fit module (G4) when it writes back to the
        store. When that schema is not present the constructor falls back
        to marginal-only.

        Raises
        ------
        KeyError
            If a parameter name in ``parameter_names`` has no matching entry.
        """
        names = tuple(parameter_names)
        matched: list[CalibrationEntry] = []
        means_list: list[float] = []
        stds_list: list[float] = []
        cov_rows: list[list[float] | None] = []

        for name in names:
            candidates = [e for e in store.entries if e.parameter_name == name]
            if not candidates:
                raise KeyError(
                    f"No CalibrationEntry found in store for parameter_name={name!r}"
                )
            entry = candidates[0]
            matched.append(entry)
            means_list.append(float(entry.measured_value))
            stds_list.append(float(entry.posterior_uncertainty))
            cov_row = entry.valid_domain.get("covariance_row") if entry.valid_domain else None
            if isinstance(cov_row, dict):
                cov_rows.append([float(cov_row.get(other_name, 0.0)) for other_name in names])
            else:
                cov_rows.append(None)

        means = np.asarray(means_list, dtype=float)
        stds = np.asarray(stds_list, dtype=float)

        covariance: np.ndarray | None
        if all(row is not None for row in cov_rows):
            cov = np.asarray(cov_rows, dtype=float)
            cov = 0.5 * (cov + cov.T)
            covariance = cov
            logger.info(
                "from_calibration_store: extracted %d parameters with full covariance",
                len(names),
            )
        else:
            covariance = None
            logger.info(
                "from_calibration_store: extracted %d parameters (marginal-only; no covariance_row)",
                len(names),
            )

        return cls(
            parameter_names=names,
            means=means,
            stds=stds,
            covariance=covariance,
            source_calibration_entries=matched,
        )


__all__ = ["PosteriorSamples", "DrawMethod"]
