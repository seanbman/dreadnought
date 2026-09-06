# Initial PR Roadmap

This sequence is a working experimental plan, not a commitment to preserve boundaries that evidence shows are wrong. When implementation diverges from the original plan, the roadmap is updated rather than rewriting the development ledgers.

## Milestone 1 — Bootstrap research substrate — merged in PR #1

Established repository conventions, ledgers, `.grapher/`, the architectural charter, and research discipline.

Merge commit: `96725840db44eef1d982b32376c69be3050cba3d`.

## Milestone 2 — Mission schema and CLI skeleton — merged in PR #2

Established the first executable contract between human intent and later agent execution: actor identity, natural-language source directive, workspace, source declarations, capability requests, lifecycle state, schema validation, and CLI creation/inspection. Mission configuration expresses requested state and does not grant authority.

Squash merge commit: `2ddda47a622cc66b90e4a5ec65ea09262e002644`.

## Milestone 3 — Doctrine, Campaign Plan, and Orders — merged in PR #3

Added the normalization and compartmentalization layer between freeform human input and execution. Doctrine captures structured intent; Campaign Plans decompose it into Operations; Project Arms receive compartmentalized Orders under the working hierarchy `Dreadnought → Task Group → Project Arm → Agent`.

Squash merge commit: `db2c89af7ffa2c803020739eec578f20bcf5850c`.

## Milestone 4 — Typed agent protocol — merged in PR #4

Introduced the small typed protocol taxonomy for claim, observation, action, artifact, requirement, risk, note, and verdict records, with explicit human-source, agent, observer, and evaluation perspectives. Agent testimony cannot self-promote into observer evidence or verdict authority.

Squash merge commit: `d6692863d9d43372f3fffc7b5c6fb821b6dafee1`.

## Milestone 5 — Grapher control-plane integration — merged in PR #5

Made Dreadnought the software authority for canonical protocol writes into Grapher while preserving the submitting actor's identity and perspective. Added validation-before-mutation, duplicate rejection, reference/evidence edges, history events, and the `protocol ingest` path.

Squash merge commit: `4630ac84da52677b343e7a3737844da683b25202`.

## Milestone 6 — Deterministic verification — merged in PR #6

Added the first verifier registry and reproducible checks for filesystem presence/absence, SHA-256 equality, and command exit status. Unsupported semantic claims remain `unverifiable` rather than being guessed.

Squash merge commit: `07721476c042df38edf6fc6fed1777a3f3c7004b`.

A documentation-index maintenance change merged separately in PR #7 at `b1852eff25b2c8b95924e134792ade74e433f255` and does not consume an architecture milestone number.

## Milestone 7 — Sarcophagus prototype — merged in PR #8

Established the first Linux execution boundary using Bubblewrap: canonical workspace read-only, external writable scratch, default network isolation, environment allowlisting, and fail-closed behavior when the sandbox backend is unavailable. This remains a prototype pending target-host adversarial testing and stronger kernel/resource controls.

Squash merge commit: `ce853e50706259b32585e7311b1d74638cb2bda5`.

PR #9 was an accidental no-op draft and was immediately closed without merge; it is retained in history rather than repurposed.

## Milestone 8 — First agent adapter and Project Arm dispatch — in progress

Launch one external agent command from a normalized Order through Dreadnought. The initial provider-neutral adapter serializes the Order into external scratch, executes through Sarcophagus, and records Dreadnought observer evidence into Grapher. A vendor-specific coding-agent adapter and real-workspace run are required before this milestone is considered empirically validated.

Working branch: `feature/project-arm-dispatch`.

## Milestone 9 — Closure and audit semantics

Separate claimed completion, deterministic verification, authority acceptance, and closure. Produce human- and machine-readable inspection reports that trace Doctrine → Operation → Order → Project Arm → PR → evidence and discrepancies.

## Deferred until evidence justifies them

Multi-Project-Arm orchestration, model training, automatic taxonomy expansion, generalized multi-provider autonomy, sophisticated inference, and broad policy engines.
