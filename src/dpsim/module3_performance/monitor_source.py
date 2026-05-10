"""Hardware-agnostic ``MonitorSource`` protocol and concrete backends.

B-3g / W-044 — v0.8.2. Per ADR-008, defines the protocol downstream UI
code consumes when reading streaming pressure-monitor data, plus three
concrete backends:

* :class:`CSVReplayMonitorSource` — wraps the v0.8.0 ``parse_csv`` /
  ``replay`` helpers; primary use case is offline replay of a recorded
  run.
* :class:`SimulatedMonitorSource` — synthetic trace generator for
  training / unit tests; produces a realistic ramp-up + plateau curve
  with optional slow-fouling slope.
* :class:`NullMonitorSource` — always returns ``None``; useful as a
  default placeholder when no source is bound.

The :class:`UnicornSocketMonitorSource` (live AKTA UNICORN bridge) is
the explicit v0.9 deliverable and is NOT in this module — see ADR-008.
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass, field
from typing import Optional, Protocol, runtime_checkable

from dpsim.module3_performance.pressure_monitor import PressureMonitorReading
from dpsim.module3_performance.pressure_monitor_replay import parse_csv


# ─── Protocol ───────────────────────────────────────────────────────────────


@runtime_checkable
class MonitorSource(Protocol):
    """Hardware-agnostic source of pressure-monitor readings.

    Consumers call ``next_reading()`` to fetch the next available
    reading or ``None`` when the source is exhausted (offline) or
    has nothing new (live, in steady-state). ``reset()`` rewinds the
    source so consumers can restart a replay or reseed a simulator.

    Implementations should be cheap to call repeatedly; UI consumers
    poll on every Streamlit rerun.
    """

    def next_reading(self) -> Optional[PressureMonitorReading]:
        """Return the next reading or ``None`` if none is available."""
        ...

    def reset(self) -> None:
        """Rewind the source to its initial state."""
        ...


# ─── CSV replay backend ─────────────────────────────────────────────────────


@dataclass
class CSVReplayMonitorSource:
    """Replay a parsed CSV trace through the ``MonitorSource`` protocol.

    Wraps :func:`dpsim.module3_performance.pressure_monitor_replay.parse_csv`.
    Each ``next_reading()`` call yields the next reading in time order
    until the trace is exhausted, then returns ``None``.
    """

    csv_text: str
    _readings: tuple[PressureMonitorReading, ...] = field(
        default_factory=tuple, init=False, repr=False,
    )
    _cursor: int = field(default=0, init=False, repr=False)

    def __post_init__(self) -> None:
        from io import StringIO
        self._readings = parse_csv(StringIO(self.csv_text))
        self._cursor = 0

    def next_reading(self) -> Optional[PressureMonitorReading]:
        if self._cursor >= len(self._readings):
            return None
        r = self._readings[self._cursor]
        self._cursor += 1
        return r

    def reset(self) -> None:
        self._cursor = 0

    @property
    def n_readings(self) -> int:
        return len(self._readings)


# ─── Simulated trace backend ────────────────────────────────────────────────


@dataclass
class SimulatedMonitorSource:
    """Synthetic pressure-trace generator for training and unit tests.

    Produces an exponential ramp-up to ``dP_steady_pa`` over
    ``ramp_seconds`` followed by an optional linear fouling rise at
    ``fouling_slope_pa_per_s``, sampled at ``sample_period_s``.

    Useful as a deterministic test fixture (set ``seed`` for repeat-
    able noise) and as a UI training mode that gives operators a
    realistic-looking trace without requiring real-run data.

    Attributes
    ----------
    Q_m3_s :
        Constant flow rate echoed on every reading.
    dP_steady_pa :
        Asymptotic steady-state ΔP.
    ramp_seconds :
        e-folding time of the exponential ramp from 0 to steady.
    fouling_slope_pa_per_s :
        Linear ΔP rise added on top of the ramp asymptote. Default 0
        (clean flow).
    sample_period_s :
        Time step between readings.
    duration_s :
        Total trace duration; ``next_reading()`` returns ``None``
        after this.
    noise_std_pa :
        Gaussian noise added to each ΔP reading (mean 0).
    seed :
        Optional RNG seed for reproducibility.
    """

    Q_m3_s: float = 1.0e-7
    dP_steady_pa: float = 50_000.0
    ramp_seconds: float = 60.0
    fouling_slope_pa_per_s: float = 0.0
    sample_period_s: float = 5.0
    duration_s: float = 600.0
    noise_std_pa: float = 0.0
    seed: Optional[int] = None
    _t: float = field(default=0.0, init=False, repr=False)
    _rng: random.Random = field(init=False, repr=False)

    def __post_init__(self) -> None:
        self._rng = random.Random(self.seed)

    def next_reading(self) -> Optional[PressureMonitorReading]:
        if self._t > self.duration_s:
            return None
        # Exponential ramp + linear fouling slope + noise.
        ramp = self.dP_steady_pa * (1.0 - math.exp(-self._t / max(self.ramp_seconds, 1e-9)))
        foul = self.fouling_slope_pa_per_s * self._t
        noise = (
            self._rng.gauss(0.0, self.noise_std_pa)
            if self.noise_std_pa > 0.0 else 0.0
        )
        dp = max(ramp + foul + noise, 0.0)
        reading = PressureMonitorReading(
            t_s=self._t,
            dP_pa=dp,
            Q_m3_s=self.Q_m3_s,
        )
        self._t += self.sample_period_s
        return reading

    def reset(self) -> None:
        self._t = 0.0
        self._rng = random.Random(self.seed)


# ─── Null backend ──────────────────────────────────────────────────────────


@dataclass
class NullMonitorSource:
    """Always returns ``None``. UI default when no source is bound."""

    def next_reading(self) -> Optional[PressureMonitorReading]:
        return None

    def reset(self) -> None:
        pass


__all__ = [
    "CSVReplayMonitorSource",
    "MonitorSource",
    "NullMonitorSource",
    "SimulatedMonitorSource",
]
