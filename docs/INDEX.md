# Dreadnought documentation index

## Index

- [Start here](#start-here)
- [Architecture](#architecture)
- [Ledgers](#ledgers)
- [Machine-readable counterparts](#machine-readable-counterparts)
- [Document authority and update rules](#document-authority-and-update-rules)
- [Current milestone boundary](#current-milestone-boundary)
- [Appendix — Process flow](#appendix--process-flow)

This is the canonical durable documentation map. **New users should begin with the root [`README.md`](../README.md).**

## Start here

- [`README.md`](../README.md) — user-friendly overview and Linux quick start.
- [`BOOTSTRAP.md`](BOOTSTRAP.md) — workspace initialization, inherited Grapher adoption, generated instructions, and nested-project routing.
- [`MISSION_BUILDER.md`](MISSION_BUILDER.md) — guided mission prompt, source-document, requirement, notes, capability, review, and readiness workflow.
- [`INSTALLATION_AND_UPDATES.md`](INSTALLATION_AND_UPDATES.md) — Linux installation, updates, release checks, dependency, troubleshooting.
- [`INLINE_CLI.md`](INLINE_CLI.md) — inline numbered/arrow-key menus, cancellation semantics, help command, and `man dreadnought`.
- [`RELEASE_0.2.0b2.md`](RELEASE_0.2.0b2.md) — current beta patch baseline and upgrade paths.
- [`RELEASE_0.2.0b1.md`](RELEASE_0.2.0b1.md) — previous beta baseline and verification.
- [`PROJECT_EXECUTION_TUTORIAL.md`](PROJECT_EXECUTION_TUTORIAL.md) — canonical setup-to-execution walkthrough.
- [`INTERACTIVE_CLI_AND_TOKEN_USAGE.md`](INTERACTIVE_CLI_AND_TOKEN_USAGE.md) — menu, primary-agent chat, configuration, token accounting.
- [`CLI_USAGE.md`](CLI_USAGE.md) — compact command reference and authority boundaries.
- [`AGENTS.md`](../AGENTS.md) — repository operating instructions.
- [`README.md`](README.md) — research-record conventions.
- [`DIAGRAM_STANDARD.md`](DIAGRAM_STANDARD.md) — documentation/diagram provenance contract.
- [`ROADMAP.md`](ROADMAP.md) — milestone sequence and deferred work.

## Architecture

- [`ARCHITECTURE.md`](ARCHITECTURE.md) — root component and trust-boundary map.
- [`ARCHITECTURE_CHARTER.md`](ARCHITECTURE_CHARTER.md) — principles and authority model.
- [`GRAPHER_INTEGRATION.md`](GRAPHER_INTEGRATION.md) — Dreadnought/Grapher authority, v0.7.0b1 compatibility, initialization, brokering, projection, publication.
- [`PROJECT_ARM_LEDGER.md`](PROJECT_ARM_LEDGER.md) — dispatch/adapters/result-channel architecture.
- [`SARCOPHAGUS_LEDGER.md`](SARCOPHAGUS_LEDGER.md) — isolation and scratch/canonical workspace architecture.
- [`PROTOCOL_LEDGER.md`](PROTOCOL_LEDGER.md) — typed epistemic protocol architecture.

## Ledgers

- [`DEVELOPMENT_LEDGER.md`](DEVELOPMENT_LEDGER.md) — chronological implementation record.
- [`DECISION_LEDGER.md`](DECISION_LEDGER.md) — decisions and supersession history.
- [`DOCUMENTATION_LEDGER.md`](DOCUMENTATION_LEDGER.md) — documentation governance and Grapher CI enforcement.
- [`EXPERIMENT_LEDGER.md`](EXPERIMENT_LEDGER.md) — hypotheses, experiments, evidence, conclusions.
- [`FAILURE_LEDGER.md`](FAILURE_LEDGER.md) — failures and lessons.
- [`PROTOCOL_LEDGER.md`](PROTOCOL_LEDGER.md) — protocol evolution.
- [`SARCOPHAGUS_LEDGER.md`](SARCOPHAGUS_LEDGER.md) — execution-isolation experiments.
- [`PROJECT_ARM_LEDGER.md`](PROJECT_ARM_LEDGER.md) — Project Arm dispatch/result-channel experiments.

## Machine-readable counterparts

Local runtime brain state lives under [`.grapher/`](../.grapher/). Git-versioned governance/publication evidence lives under [`.grapher/shared/`](../.grapher/shared/). Dreadnought project configuration/token accounting and mission documents live under [`.dreadnought/`](../.dreadnought/). Contracts are under [`schemas/`](../schemas/), executable code under [`src/dreadnought/`](../src/dreadnought/), verification under [`tests/`](../tests/). Dreadnought runtime Grapher mutations pass through `GrapherControlPlane`; repository changes carry versioned Grapher evidence.

## Document authority and update rules

Current typed schema/code and validated machine state define executable behavior; the Architecture Charter/current decisions define intended architecture; Roadmap defines active sequence; ledgers preserve contemporaneous beliefs. CLI parser/help is executable authority. [`BOOTSTRAP.md`](BOOTSTRAP.md) is workspace-initialization authority, [`MISSION_BUILDER.md`](MISSION_BUILDER.md) is mission-authoring authority, [`INSTALLATION_AND_UPDATES.md`](INSTALLATION_AND_UPDATES.md) is distribution authority, [`INLINE_CLI.md`](INLINE_CLI.md) is interactive-terminal authority, and [`PROJECT_EXECUTION_TUTORIAL.md`](PROJECT_EXECUTION_TUTORIAL.md) is the canonical execution walkthrough. New durable Markdown must be indexed here, contain `## Index`, and include the required Mermaid provenance appendix. Architecture-bearing docs link to [`ARCHITECTURE.md`](ARCHITECTURE.md).

## Current milestone boundary

Current public beta: **Dreadnought v0.2.0b2** with **Grapher v0.7.0b1**. v0.2.0b2 adds guided Mission Builder, mission review/readiness flows, in-place `dreadnought update`, local-checkout installation, and explicit `--version`. The inline terminal UX pass replaces full-screen dialogs and adds reliable cancellation/help/manual support without changing Dreadnought's control-plane authority. Existing Project Arm/Sarcophagus/typed-protocol/Grapher/token-accounting capabilities remain. The bootstrap initialization work adds inherited-brain adoption and generated workspace instructions on the current development line. Next empirical milestone: real vendor adapter plus bounded real-workspace run.

## Appendix — Process flow

```mermaid
flowchart LR
    R["User entry point\ncode: README.md; install.sh\ninception: 3bea73dd2ca73199b86b49998e049fb0f30c454f\ncurrent: fix/bootstrap-initialization-flow"] --> I["Canonical docs index\ncode: docs/INDEX.md; tests/test_documentation.py\ninception: b1852eff25b2c8b95924e134792ade74e433f255\ncurrent: fix/bootstrap-initialization-flow"]
    I --> B["Workspace bootstrap\ncode: docs/BOOTSTRAP.md; src/dreadnought/bootstrap.py\ninception: a72edbfe4df191e5d9570c9dcf6d55909a1893ce\ncurrent: fix/bootstrap-initialization-flow"]
    I --> M["Mission Builder\ncode: docs/MISSION_BUILDER.md; src/dreadnought/mission_builder.py\ninception: 9808bfe5d35beabd950b0fff1487c452494cf597\ncurrent: f9be45cc"]
    I --> T["Inline terminal UX\ncode: docs/INLINE_CLI.md; src/dreadnought/interactive.py; man/dreadnought.1\ninception: f9be45cc\ncurrent: ux/inline-cli-menus-help"]
    I --> U["Beta distribution/update\ncode: docs/INSTALLATION_AND_UPDATES.md; install.sh; src/dreadnought/update.py\ninception: cae9fc9ef9a1f5ae8313cce0811fcdb0ae1d1d2e\ncurrent: ux/inline-cli-menus-help"]
```
