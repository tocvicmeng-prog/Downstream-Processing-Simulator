# ADR-008 — Monitor source abstraction: hardware-agnostic surface

**Status:** Accepted
**Date:** 2026-05-10
**Decision driver:** v0.8.2 W-044. The v0.8.0 plan §6 deferred "Live AKTA UNICORN integration — WebSocket bridge to UNICORN data stream" and the v0.8.1 release handover catalogued it as a remaining cumulative open item. The full live socket bridge depends on hardware availability that DPSim's developers do not have; this ADR + the accompanying ``monitor_source.py`` ship the **abstraction** so downstream UI code is hardware-agnostic, leaving the concrete UNICORN backend as the explicit v0.9 binding-open part.

## Context

The v0.7.0 streaming pressure monitor (`evaluate_pressure_trace`) and
the v0.8.0 streaming UI (`pressure_monitor_replay`) consume
`PressureMonitorReading` instances. v0.8.0 ships only one source: a
CSV file uploaded by the operator. Live ÄKTA UNICORN integration
(via UNICORN's RealTime API or its OPC-UA server) is the natural
next step — but:

1. UNICORN's API requires an active running instrument; DPSim's
   developers don't have one in the test environment.
2. The protocol details (HTTP polling vs WebSocket vs OPC-UA) are
   site-specific — different labs configure UNICORN differently.
3. Operators training on DPSim before they have hardware access need
   a *simulator* path that produces realistic synthetic traces.

A single-class architecture ("just hardcode UNICORN") would couple
the UI to one vendor and one transport. A protocol-typed
abstraction lets the same UI consume CSV replay (training mode),
synthetic streams (training-mode-without-CSV), or live UNICORN
sockets (production) without code changes.

## Decision

**Ship a `MonitorSource` typing.Protocol with three concrete
backends in v0.8.2; defer the UNICORN backend to v0.9.**

```python
class MonitorSource(Protocol):
    """Source of pressure-monitor readings (offline or live)."""
    def next_reading(self) -> Optional[PressureMonitorReading]: ...
    def reset(self) -> None: ...
```

Concrete backends shipping in v0.8.2:

| Backend | Use case | Status |
|---|---|---|
| `CSVReplayMonitorSource` | Offline replay of a recorded run; the existing v0.8.0 flow | LANDS THIS RELEASE |
| `SimulatedMonitorSource` | Synthetic trace generator for training and unit tests; produces a realistic ramp-up + plateau curve with optional fouling slope | LANDS THIS RELEASE |
| `NullMonitorSource` | Always returns ``None``; useful as a default placeholder in tests / UI when no source is bound | LANDS THIS RELEASE |
| `UnicornSocketMonitorSource` | Live AKTA UNICORN bridge | **DEFERRED to v0.9** |

The deferred UNICORN backend has these requirements documented for
future implementation:

1. **Transport.** UNICORN exposes an OPC-UA server (with cert auth)
   and an HTTP "Real-Time" feed (polled, JSON). DPSim should wrap
   both behind the `MonitorSource` protocol; site config picks one.
2. **Reading mapping.** UNICORN reports pressure in MPa, flow in
   mL/min — convert to SI (Pa, m³/s) at the boundary.
3. **Hardware-side test fixture.** A staging UNICORN instance with
   a recorded run replayed in real-time is the canonical test
   environment; DPSim cannot ship CI for the live backend without it.
4. **Thread/async model.** The UI is Streamlit (synchronous reruns).
   The live backend should poll on a worker thread and buffer
   readings; the protocol is synchronous from the UI's perspective.
5. **Failure modes.** Lost connection, instrument paused, calibration
   reset — all should drop a `MonitorSourceError` rather than
   returning a degraded `PressureMonitorReading`.

## Consequences

- **UI becomes hardware-agnostic.** The streaming-monitor section in
  `tab_m3_monitor.py` is updated to take an optional `MonitorSource`
  argument; when supplied, it polls via `next_reading()` instead of
  parsing an uploaded CSV. Default remains the CSV path for backwards
  compatibility.
- **Training mode is testable today.** The `SimulatedMonitorSource`
  ships a deterministic trace synthesizer that generates a
  steady-state + slow-fouling pattern, parameterizable by random
  seed; consumers can build training scenarios without recorded data.
- **v0.9 hardware sprint is a contained task.** Adding the UNICORN
  backend requires only a new class implementing the protocol — the
  UI, replay logic, and tests are unchanged.

## Out of scope

- The actual UNICORN backend (v0.9, gated on hardware access).
- Multi-instrument live aggregation (parallel runs from multiple
  ÄKTAs into a single dashboard).
- Buffered persistent recording — the live source can stream to a
  CSV via existing replay primitives, but a dedicated recording
  mechanism is v0.9+ scope.

## References

- ADR-007 — Forward Monte Carlo Bayesian envelope (the MC wrapper
  is independent but consumes the same `PressureMonitorReading`
  flow type).
- v0.7.0 work plan §6 deferral of "Streaming UI for evaluate_pressure_trace"
  (closed at v0.8.0 for offline; v0.8.2 closes the abstraction;
  v0.9 closes the live backend).
- AKTA UNICORN OPC-UA Programmer's Guide (Cytiva, internal — vendor
  documentation; not redistributable).
