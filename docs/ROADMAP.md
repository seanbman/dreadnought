# Initial PR Roadmap

This sequence is a working experimental plan, not a commitment to preserve boundaries that evidence shows are wrong.

## PR 1 — Bootstrap research substrate and mission schema

Establish repository conventions, ledgers, `.grapher/`, architectural charter, CLI skeleton, actor identity, mission schema, source declarations, capability declarations, and explicit lifecycle state. Avoid real agent autonomy at this stage.

## PR 2 — Typed agent protocol

Introduce a deliberately small first taxonomy for structured records such as claim, observation, action, artifact, requirement, risk, note, and verdict. Define schema validation and separate human notes from machine-significant semantics.

## PR 3 — Grapher control-plane integration

Route protocol records through Dreadnought into Grapher. Establish explicit agent and observer perspectives, provenance, immutability/supersession behavior, and control-plane write ownership.

## PR 4 — Deterministic verification

Implement verifier interfaces for command results, filesystem state, Git state, tests/builds, hashes/diffs, and similarly observable predicates. Preserve supported, contradicted, partial, and unverified outcomes.

## PR 5 — Sarcophagus prototype

Prototype the Linux execution boundary: canonical workspace read-only, writable scratch/overlay, bounded process/network/filesystem capabilities, and Dreadnought-mediated authoritative mutations.

## PR 6 — First real agent adapter

Launch one external coding agent from a normalized mission through Dreadnought. Record its structured claims and Dreadnought's independent observations. Prefer one agent and one real workspace before minion orchestration.

## PR 7 — Closure and audit semantics

Separate claimed completion, verification, user/authority acceptance, and closure. Produce a human- and machine-readable mission inspection report showing evidence and discrepancies.

## Deferred until evidence justifies them

Minion orchestration, model training, automatic taxonomy expansion, generalized multi-provider autonomy, sophisticated inference, and broad policy engines.
