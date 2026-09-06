# Dreadnought Architecture Charter

**Status:** initial working charter  
**Date:** 2026-09-06

Dreadnought is an experimental agent control plane. Its purpose is not merely to prompt agents but to mediate their authority, normalize missions and machine-significant claims, observe execution independently, preserve provenance, and verify claims against deterministic evidence where possible.

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

## Initial conceptual components

- Mission compiler
- Agent/control API
- Capability and policy layer
- Agent adapter(s)
- Sarcophagus execution boundary
- Observer/event recorder
- Deterministic verifier registry
- Grapher adapter/evidence store
- Human-facing inspection and audit interface

This charter is intentionally not a frozen specification. Changes should be recorded in the Decision Ledger and, where testable, the Experiment Ledger.
