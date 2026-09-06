# Dreadnought documentation index

This is the canonical index for the repository's human-readable record. Use it to locate the current architectural contract, chronological research record, protocol notes, and forward plan without scanning the repository tree.

## Start here

- [`README.md`](../README.md) — project overview and entry point.
- [`AGENTS.md`](../AGENTS.md) — repository operating instructions for agents and contributors.
- [`docs/README.md`](README.md) — research-record conventions and maintenance discipline.
- [`ARCHITECTURE_CHARTER.md`](ARCHITECTURE_CHARTER.md) — current architectural principles and system boundaries.
- [`ROADMAP.md`](ROADMAP.md) — current PR sequence, completed milestones, and deferred work.

## Ledgers

Ledgers are append-oriented research records. They should preserve historical mistakes, uncertainty, and superseded thinking rather than being rewritten into a clean retrospective.

- [`DEVELOPMENT_LEDGER.md`](DEVELOPMENT_LEDGER.md) — chronological implementation record: what changed, why, relevant commits/PRs, limitations, and next questions.
- [`DECISION_LEDGER.md`](DECISION_LEDGER.md) — architectural decisions, rationale, alternatives, status, and supersession history.
- [`EXPERIMENT_LEDGER.md`](EXPERIMENT_LEDGER.md) — hypotheses, experiments, expected evidence, observed results, and conclusions.
- [`FAILURE_LEDGER.md`](FAILURE_LEDGER.md) — failures, contamination events, false assumptions, and lessons carried forward.
- [`PROTOCOL_LEDGER.md`](PROTOCOL_LEDGER.md) — evolution of typed protocol semantics, actor/perspective boundaries, and machine-significant record taxonomy.

## Machine-readable counterparts

Human-readable Markdown is not the canonical machine evidence store. Machine-readable state lives under [`.grapher/`](../.grapher/):

- `.grapher/knowledge.json` — canonical graph state.
- `.grapher/history.jsonl` — append-oriented history/evidence events.
- `.grapher/config.json` — project Grapher configuration.

Versioned wire/data contracts live under [`schemas/`](../schemas/). Executable control-plane code lives under [`src/dreadnought/`](../src/dreadnought/), with verification under [`tests/`](../tests/).

## Document authority and update rules

When documents disagree, do not silently reconcile them. Prefer the most specific authoritative source for the question, then record the discrepancy if it matters:

1. Current typed schema/code and validated machine state define executable behavior.
2. `ARCHITECTURE_CHARTER.md` and current decisions define intended architecture.
3. `ROADMAP.md` defines the active development sequence.
4. Ledgers preserve what was believed and observed at the time; historical entries are not rewritten merely because later decisions changed.
5. Freeform notes never silently become machine authority.

When adding a new durable Markdown document under `docs/`, add it to this index in the same PR. New specialized ledgers should also be linked from `docs/README.md`.

## Current milestone boundary

As of the completion of PR #6, Dreadnought has established mission/Doctrine/Order models, typed protocol records, the Dreadnought-owned Grapher software write boundary, and the first deterministic verifier registry. The next roadmap milestone is the Sarcophagus execution-boundary prototype.
