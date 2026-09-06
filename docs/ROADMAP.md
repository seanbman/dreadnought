# Initial PR Roadmap

This sequence is a working experimental plan, not a commitment to preserve boundaries that evidence shows are wrong. When implementation diverges from the original plan, the roadmap is updated rather than rewriting the development ledgers.

## PR 1 — Bootstrap research substrate — merged

Established repository conventions, ledgers, `.grapher/`, the architectural charter, and research discipline. The original roadmap also placed the mission schema and CLI skeleton here; those were intentionally deferred so the research substrate could be reviewed as its own boundary.

Merge commit: `96725840db44eef1d982b32376c69be3050cba3d`.

## PR 2 — Mission schema and CLI skeleton — in progress

Establish the first executable contract between human intent and later agent execution: actor identity, natural-language source directive, workspace, source declarations, capability requests, lifecycle state, schema validation, and CLI creation/inspection. No real agent autonomy yet.

## PR 3 — Doctrine, campaign plan, and orders

Introduce the normalization layer between freeform human input and agent execution. Dreadnought ingests human directives and supporting material, records source provenance in the project `.grapher/`, and compiles accepted intent into a versioned Doctrine document.

Doctrine defines objectives, requirements, constraints, priorities, acceptance conditions, unresolved questions, and explicit creative-authority envelopes. Dreadnought then decomposes Doctrine into a Campaign Plan containing PR-sized Operations and issues compartmentalized Orders to Project Arms.

Standard hierarchy:

`Dreadnought → Task Group → Project Arm → Agent`

Orders should expose only the project context, source excerpts, graph nodes, dependencies, acceptance predicates, capabilities, and creative latitude required for that Operation. Project-wide strategic context remains with Dreadnought unless explicitly needed.

## PR 4 — Typed agent protocol

Introduce a deliberately small first taxonomy for structured records such as claim, observation, action, artifact, requirement, risk, note, and verdict. Define schema validation and separate human notes from machine-significant semantics.

## PR 5 — Grapher control-plane integration

Route Doctrine provenance, Operations, Orders, and typed protocol records through Dreadnought into Grapher. Establish explicit human-source, agent, observer, and evaluation perspectives; provenance; immutability/supersession behavior; and control-plane write ownership.

## PR 6 — Deterministic verification

Implement verifier interfaces for command results, filesystem state, Git state, tests/builds, hashes/diffs, and similarly observable predicates. Preserve supported, contradicted, partial, and unverified outcomes.

## PR 7 — Sarcophagus prototype

Prototype the Linux execution boundary: canonical workspace read-only, writable scratch/overlay, bounded process/network/filesystem capabilities, and Dreadnought-mediated authoritative mutations.

## PR 8 — First real agent adapter and Project Arm dispatch

Launch one external coding agent from a normalized Order through Dreadnought. Record its structured claims and Dreadnought's independent observations. Start with one Project Arm and one real workspace before multi-arm orchestration.

## PR 9 — Closure and audit semantics

Separate claimed completion, deterministic verification, authority acceptance, and closure. Produce human- and machine-readable inspection reports that trace Doctrine → Operation → Order → Project Arm → PR → evidence and discrepancies.

## Deferred until evidence justifies them

Multi-Project-Arm orchestration, model training, automatic taxonomy expansion, generalized multi-provider autonomy, sophisticated inference, and broad policy engines.
