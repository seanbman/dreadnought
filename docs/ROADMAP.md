# Initial PR Roadmap

This sequence is a working experimental plan, not a commitment to preserve boundaries that evidence shows are wrong. When implementation diverges from the original plan, the roadmap is updated rather than rewriting the development ledgers.

## PR 1 — Bootstrap research substrate — merged

Established repository conventions, ledgers, `.grapher/`, the architectural charter, and research discipline. The original roadmap also placed the mission schema and CLI skeleton here; those were intentionally deferred so the research substrate could be reviewed as its own boundary.

Merge commit: `96725840db44eef1d982b32376c69be3050cba3d`.

## PR 2 — Mission schema and CLI skeleton — in progress

Establish the first executable contract between human intent and later agent execution: actor identity, natural-language source directive, workspace, source declarations, capability requests, lifecycle state, schema validation, and CLI creation/inspection. No real agent autonomy yet.

## PR 3 — Typed agent protocol

Introduce a deliberately small first taxonomy for structured records such as claim, observation, action, artifact, requirement, risk, note, and verdict. Define schema validation and separate human notes from machine-significant semantics.

## PR 4 — Grapher control-plane integration

Route protocol records through Dreadnought into Grapher. Establish explicit agent and observer perspectives, provenance, immutability/supersession behavior, and control-plane write ownership.

## PR 5 — Deterministic verification

Implement verifier interfaces for command results, filesystem state, Git state, tests/builds, hashes/diffs, and similarly observable predicates. Preserve supported, contradicted, partial, and unverified outcomes.

## PR 6 — Sarcophagus prototype

Prototype the Linux execution boundary: canonical workspace read-only, writable scratch/overlay, bounded process/network/filesystem capabilities, and Dreadnought-mediated authoritative mutations.

## PR 7 — First real agent adapter

Launch one external coding agent from a normalized mission through Dreadnought. Record its structured claims and Dreadnought's independent observations. Prefer one agent and one real workspace before minion orchestration.

## PR 8 — Closure and audit semantics

Separate claimed completion, verification, user/authority acceptance, and closure. Produce a human- and machine-readable mission inspection report showing evidence and discrepancies.

## Deferred until evidence justifies them

Minion orchestration, model training, automatic taxonomy expansion, generalized multi-provider autonomy, sophisticated inference, and broad policy engines.
