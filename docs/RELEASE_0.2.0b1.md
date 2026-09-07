# Dreadnought v0.2.0b1 beta release

## Index

- [Status](#status)
- [What changed](#what-changed)
- [Installation](#installation)
- [Grapher compatibility](#grapher-compatibility)
- [Verification](#verification)
- [Current boundary](#current-boundary)
- [Appendix — Process flow](#appendix--process-flow)

## Status

v0.2.0b1 is the current public Dreadnought beta, published as a GitHub prerelease from merge commit `cae9fc9ef9a1f5ae8313cce0811fcdb0ae1d1d2e`.

## What changed

The beta establishes a Linux end-user distribution path with a no-sudo per-user installer, isolated environment, launcher under `~/.local/bin`, semantic-version GitHub Release discovery, non-blocking interactive update notices, and automated beta publication. It retains the existing long-form CLI as the deterministic automation interface.

## Installation

Use [`INSTALLATION_AND_UPDATES.md`](INSTALLATION_AND_UPDATES.md). For actual project operation after installation, continue with [`PROJECT_EXECUTION_TUTORIAL.md`](PROJECT_EXECUTION_TUTORIAL.md).

## Grapher compatibility

Dreadnought v0.2.0b1 consumes the published Grapher v0.7.0b1 beta. Dreadnought remains the controlled-workspace admission/write mediator; Grapher remains responsible for durable representation, truth policy, semantic integrity, transitions, history, rollback, and publication semantics.

## Verification

The beta CI installed Dreadnought from its package metadata against the published Grapher v0.7.0b1 dependency and passed the repository test suite plus the mandatory Grapher shared-state governance gate before merge and prerelease publication.

## Current boundary

This beta does not claim empirical completion of the Project Arm architecture. A real vendor adapter and bounded real-workspace execution remain the next validation milestone. Process exit alone is not acceptance.

## Appendix — Process flow

```mermaid
flowchart LR
    G["Published Grapher v0.7.0b1\ncode: pyproject.toml; src/dreadnought/grapher.py\ninception dependency: e5f7fd3ea981359df97703d8b3ce8fbcdff468cd\ncurrent beta: cae9fc9ef9a1f5ae8313cce0811fcdb0ae1d1d2e"] --> C["Dreadnought beta CI\ncode: .github/workflows/test.yml\ninception/current beta: cae9fc9ef9a1f5ae8313cce0811fcdb0ae1d1d2e"] --> R["GitHub prerelease v0.2.0b1\ncode: .github/workflows/publish-beta.yml\ninception/current beta: cae9fc9ef9a1f5ae8313cce0811fcdb0ae1d1d2e"] --> I["Linux install/update flow\ncode: install.sh; src/dreadnought/update.py\ninception/current beta: cae9fc9ef9a1f5ae8313cce0811fcdb0ae1d1d2e"]
```
