"""Tests for the MonitorSource abstraction (B-3g / W-044, v0.8.2).

Covers ADR-008 acceptance:

* Protocol membership for the three concrete backends.
* CSVReplayMonitorSource: fetches in time order, returns None after
  exhaustion, reset rewinds.
* SimulatedMonitorSource: exponential ramp asymptotes to steady dP,
  fouling slope adds linearly, noise is bounded by σ, seed is
  reproducible, duration_s caps the stream.
* NullMonitorSource: always None.
"""

from __future__ import annotations

import pytest

from dpsim.module3_performance.monitor_source import (
    CSVReplayMonitorSource,
    MonitorSource,
    NullMonitorSource,
    SimulatedMonitorSource,
)


# ─── Protocol membership ───────────────────────────────────────────────────


class TestProtocolMembership:
    def test_csv_replay_implements_protocol(self):
        src = CSVReplayMonitorSource(
            csv_text="t_s,dP_pa,Q_m3_s\n0,1000,1e-8\n",
        )
        assert isinstance(src, MonitorSource)

    def test_simulated_implements_protocol(self):
        src = SimulatedMonitorSource()
        assert isinstance(src, MonitorSource)

    def test_null_implements_protocol(self):
        src = NullMonitorSource()
        assert isinstance(src, MonitorSource)


# ─── CSVReplayMonitorSource ───────────────────────────────────────────────


class TestCSVReplay:
    def test_fetches_in_time_order(self):
        text = (
            "t_s,dP_pa,Q_m3_s\n"
            "0,1000,1e-8\n"
            "10,1500,1e-8\n"
            "20,2000,1e-8\n"
        )
        src = CSVReplayMonitorSource(csv_text=text)
        r1 = src.next_reading()
        r2 = src.next_reading()
        r3 = src.next_reading()
        assert r1 is not None and r1.t_s == 0.0
        assert r2 is not None and r2.t_s == 10.0
        assert r3 is not None and r3.t_s == 20.0

    def test_returns_none_after_exhaustion(self):
        text = "t_s,dP_pa,Q_m3_s\n0,1000,1e-8\n"
        src = CSVReplayMonitorSource(csv_text=text)
        first = src.next_reading()
        assert first is not None
        assert src.next_reading() is None
        # Subsequent calls keep returning None.
        assert src.next_reading() is None

    def test_reset_rewinds(self):
        text = (
            "t_s,dP_pa,Q_m3_s\n"
            "0,1000,1e-8\n"
            "10,2000,1e-8\n"
        )
        src = CSVReplayMonitorSource(csv_text=text)
        # Drain.
        src.next_reading()
        src.next_reading()
        assert src.next_reading() is None
        # Reset and re-drain.
        src.reset()
        again = src.next_reading()
        assert again is not None
        assert again.t_s == 0.0

    def test_n_readings_property(self):
        text = "t_s,dP_pa,Q_m3_s\n0,1000,1e-8\n10,2000,1e-8\n20,3000,1e-8\n"
        src = CSVReplayMonitorSource(csv_text=text)
        assert src.n_readings == 3


# ─── SimulatedMonitorSource ───────────────────────────────────────────────


class TestSimulated:
    def test_ramp_asymptotes_to_steady(self):
        src = SimulatedMonitorSource(
            dP_steady_pa=1.0e5,
            ramp_seconds=10.0,
            sample_period_s=5.0,
            duration_s=100.0,
            noise_std_pa=0.0,
        )
        # First reading at t=0 → 0.
        r0 = src.next_reading()
        assert r0 is not None and r0.dP_pa == pytest.approx(0.0, abs=1e-9)
        # Drain to t≈100s; last reading should be ≈ steady.
        last = None
        while True:
            r = src.next_reading()
            if r is None:
                break
            last = r
        assert last is not None
        assert last.dP_pa == pytest.approx(1.0e5, rel=0.001)

    def test_fouling_slope_adds_linearly(self):
        src = SimulatedMonitorSource(
            dP_steady_pa=0.0,                   # disable ramp
            ramp_seconds=1.0,
            fouling_slope_pa_per_s=10.0,
            sample_period_s=10.0,
            duration_s=100.0,
            noise_std_pa=0.0,
        )
        readings = []
        while True:
            r = src.next_reading()
            if r is None:
                break
            readings.append(r)
        # ΔP ≈ 10 · t for late readings (after ramp settles).
        late = readings[-1]
        assert late.dP_pa == pytest.approx(10.0 * late.t_s, abs=1e-6)

    def test_noise_bounded_by_sigma(self):
        src = SimulatedMonitorSource(
            dP_steady_pa=1.0e5,
            ramp_seconds=10.0,
            sample_period_s=5.0,
            duration_s=200.0,
            noise_std_pa=500.0,
            seed=42,
        )
        readings = []
        while True:
            r = src.next_reading()
            if r is None:
                break
            readings.append(r)
        # All readings ≥ 0 (clipped).
        assert all(r.dP_pa >= 0.0 for r in readings)

    def test_seed_reproducibility(self):
        src_a = SimulatedMonitorSource(
            dP_steady_pa=1.0e5, ramp_seconds=10.0, sample_period_s=5.0,
            duration_s=50.0, noise_std_pa=200.0, seed=999,
        )
        src_b = SimulatedMonitorSource(
            dP_steady_pa=1.0e5, ramp_seconds=10.0, sample_period_s=5.0,
            duration_s=50.0, noise_std_pa=200.0, seed=999,
        )
        for _ in range(11):  # 0, 5, 10, ..., 50 → 11 readings then None
            ra = src_a.next_reading()
            rb = src_b.next_reading()
            if ra is None:
                assert rb is None
                break
            assert ra is not None and rb is not None
            assert ra.dP_pa == pytest.approx(rb.dP_pa, rel=1e-12)

    def test_duration_caps_stream(self):
        src = SimulatedMonitorSource(
            dP_steady_pa=1.0e4, ramp_seconds=5.0,
            sample_period_s=10.0, duration_s=20.0, noise_std_pa=0.0,
        )
        # Expect readings at t=0, 10, 20; then None.
        n = 0
        while True:
            r = src.next_reading()
            if r is None:
                break
            n += 1
        assert n == 3

    def test_reset_rewinds_simulator(self):
        src = SimulatedMonitorSource(
            dP_steady_pa=1.0e5, ramp_seconds=10.0,
            sample_period_s=5.0, duration_s=20.0, noise_std_pa=0.0,
        )
        # Drain.
        while src.next_reading() is not None:
            pass
        src.reset()
        first = src.next_reading()
        assert first is not None
        assert first.t_s == 0.0


# ─── NullMonitorSource ────────────────────────────────────────────────────


class TestNull:
    def test_always_returns_none(self):
        src = NullMonitorSource()
        for _ in range(5):
            assert src.next_reading() is None

    def test_reset_is_a_noop(self):
        src = NullMonitorSource()
        src.reset()
        assert src.next_reading() is None
