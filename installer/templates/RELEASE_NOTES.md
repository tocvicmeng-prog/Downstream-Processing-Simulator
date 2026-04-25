# DPSim 0.1.0 - Release Notes

**Release date:** 2026-04-25

Initial Downstream Processing Simulator fork release.

This package renames the application to **Downstream Processing Simulator**
and ships the first DPSim lifecycle path:

- M1 double-emulsification microsphere fabrication.
- M2 reinforcement, activation, ligand coupling, quenching, and washing.
- M3 affinity-chromatography breakthrough screening.
- CLI entry points under `dpsim`.
- DPSim-owned runtime temp, cache, and output directories.

The inherited scientific solvers remain available while the platform moves
toward the clean-slate lifecycle architecture documented in `docs/`.
