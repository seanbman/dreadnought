# Initial PR Roadmap

This sequence is a working experimental plan, not a commitment to preserve boundaries that evidence shows are wrong. When implementation diverges from the original plan, the roadmap is updated rather than rewriting the development ledgers.

## PR 1 — Bootstrap research substrate — merged

Established repository conventions, ledgers, `.grapher/`, the architectural charter, and research discipline.

Merge commit: `96725840db44eef1d982b32376c69be3050cba3d`.

## PR 2 — Mission schema and CLI skeleton — merged

Established the first executable contract between human intent and later agent execution: actor identity, natural-language source directive, workspace, source declarations, capability requests, lifecycle state, schema validation, and CLI creation/inspection. Mission configuration expresses requested state and does not grant authority.

Squash merge commit: `2ddda47a622cc66b90e4a5ec65ea09262e002644`.

## PR 3 — Doctrine, Campaign Plan, and Orders — merged

Added the normalization and compartmentalization layer between freeform human input and execution. Doctrine captures structured intent; Campaign Plans decompose it into Operations; Project Arms receive compartmentalized Orders under the working hierarchy `Dreadnought → Task Group → Project Arm → Agent`.

Squash merge commit: `db2c89af7ffa2c803020739eec578f20bcf5850c`.

## PR 4 — Typed agent protocol — merged

Introduced the small typed protocol taxonomy for claim, observation, action, artifact, requirement, risk, note, and verdict records, with explicit human-source, agent, observer, and evaluation perspectives. Agent testimony cannot self-promote into observer evidence or verdict authority.

Squash merge commit: `d6692863d9d43372f3fffc7b5c6fb821b6dafee1`.

## PR 5 — Grapher control-plane integration — merged

Made Dreadnought the software authority for canonical protocol writes into Grapher while preserving the submitting actor's identity and perspective. Added validation-before-mutation, duplicate rejection, reference/evidence edges, history events, and the `protocol ingest` path.

Squash merge commit: `4630ac84da52677b343e7a3737844da683b25202`.

## PR 6 — Deterministic verification — merged

Added the first verifier registry and reproducible checks for filesystem presence/absence, SHA-256 equality, and command exit status. Unsupported semantic claims remain `unverifiable` rather than being guessed.

Squash merge commit: `07721476c042df38edf6fc6fed1777a3f3c7004b`.

## PR 7 — Sarcophagus prototype — next

Prototype the Linux execution boundary: canonical workspace read-only, writable scratch/overlay, bounded process/network/filesystem capabilities, and Dreadnought-mediated authoritative mutations. The core research question is whether software authority boundaries established in PRs #4–#6 can be made enforceable at the OS/filesystem level without making normal development unusably rigid.

## PR 8 — First real agent adapter and Project Arm dispatch

Launch one external coding agent from a normalized Order through Dreadnought. Record its typed claims and Dreadnought's independent observations. Start with one Project Arm and one real workspace before multi-arm orchestration.

## PR 9 — Closure and audit semantics

Separate claimed completion, deterministic verification, authority acceptance, and closure. Produce human- and machine-readable inspection reports that trace Doctrine → Operation → Order → Project Arm → PR → evidence and discrepancies.

## Deferred until evidence justifies them

Multi-Project-Arm orchestration, model training, automatic taxonomy expansion, generalized multi-provider autonomy, sophisticated inference, and broad policy engines.
