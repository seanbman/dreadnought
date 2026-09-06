# Dreadnought Architecture Charter

**Status:** initial working charter  
**Date:** 2026-09-06

## Index

- [Purpose](#purpose)
- [Working principles](#working-principles)
- [Initial conceptual components](#initial-conceptual-components)
- [Appendix — Process flow](#appendix--process-flow)

## Purpose

Dreadnought is an experimental agent control plane. Its purpose is not merely to prompt agents but to mediate their authority, normalize missions and machine-significant claims, observe execution independently, preserve provenance, and verify claims against deterministic evidence where possible. [Process map](#appendix--process-flow)

## Working principles

1. **Human intent is compiled, not blindly executed.** Natural-language directives are normalized into schema-backed mission protocols bounded by explicit policy.
2. **Authority lives in the control plane.** Agents receive capabilities; they do not inherit unrestricted control-plane authority.
3. **Agent testimony and observer evidence are separate.** What an agent claims happened must remain distinguishable from what Dreadnought observed.
4. **Verification is predicate-based.** Dreadnought assigns hard machine verdicts only where a claim maps to a deterministic verifier. `unverified`/`unverifiable` are legitimate outcomes.
5. **History is preserved.** Corrections, contradictions, supersession, and later evidence should not erase earlier records.
6. **Natural language is primarily human-facing.** Notes and rationale remain important, but machine-significant semantics should migrate to typed protocol records.
7. **Grapher is the evidence substrate.** Dreadnought may own privileged Grapher interaction while Grapher remains separable as a component.
8. **Taxonomy is empirical.** Start small; extend enums and schemas in response to actual missions, ambiguous mappings, and failures.
9. **Fail closed on authoritative mutation.** A missing evidence/control path should not silently downgrade into unrecorded mutation.
10. **The system itself is studied.** Development decisions, experiments, regressions, and failures are versioned as research evidence.

[Process map](#appendix--process-flow)

## Initial conceptual components

Mission compiler; Agent/control API; capability and policy layer; agent adapters; Sarcophagus execution boundary; observer/event recorder; deterministic verifier registry; Grapher adapter/evidence store; human-facing inspection and audit interface. This charter is intentionally not frozen. Changes should be recorded in the Decision Ledger and, where testable, the Experiment Ledger. [Process map](#appendix--process-flow)

## Appendix — Process flow

```mermaid
flowchart LR
    H["Human mission<br/>inception: 2ddda47a622cc66b90e4a5ec65ea09262e002644<br/>current: f8f40d1d072d0c37a1ba4d63c430a234339c1a54"] --> D["Doctrine / Order<br/>inception: db2c89af7ffa2c803020739eec578f20bcf5850c<br/>current: f8f40d1d072d0c37a1ba4d63c430a234339c1a54"]
    D --> S["Sarcophagus / Project Arm<br/>inception: ce853e50706259b32585e7311b1d74638cb2bda5<br/>current: f8f40d1d072d0c37a1ba4d63c430a234339c1a54"]
    S --> T["Agent testimony<br/>inception: d6692863d9d43372f3fffc7b5c6fb821b6dafee1<br/>current: f8f40d1d072d0c37a1ba4d63c430a234339c1a54"]
    S --> O["Observer evidence<br/>inception: 4630ac84da52677b343e7a3737844da683b25202<br/>current: f8f40d1d072d0c37a1ba4d63c430a234339c1a54"]
    T --> V["Deterministic verification<br/>inception: 07721476c042df38edf6fc6fed1777a3f3c7004b<br/>current: f8f40d1d072d0c37a1ba4d63c430a234339c1a54"]
    O --> V --> G["Grapher provenance<br/>inception: 4630ac84da52677b343e7a3737844da683b25202<br/>current: f8f40d1d072d0c37a1ba4d63c430a234339c1a54"]
```

Commit references: [mission](https://github.com/seanbman/dreadnought/commit/2ddda47a622cc66b90e4a5ec65ea09262e002644), [Doctrine/Orders](https://github.com/seanbman/dreadnought/commit/db2c89af7ffa2c803020739eec578f20bcf5850c), [protocol](https://github.com/seanbman/dreadnought/commit/d6692863d9d43372f3fffc7b5c6fb821b6dafee1), [Grapher](https://github.com/seanbman/dreadnought/commit/4630ac84da52677b343e7a3737844da683b25202), [verification](https://github.com/seanbman/dreadnought/commit/07721476c042df38edf6fc6fed1777a3f3c7004b), [Sarcophagus](https://github.com/seanbman/dreadnought/commit/ce853e50706259b32585e7311b1d74638cb2bda5), [current snapshot](https://github.com/seanbman/dreadnought/commit/f8f40d1d072d0c37a1ba4d63c430a234339c1a54).
