# Agent instructions

Dreadnought is being developed as both software and a research study. Preserve both machine-readable provenance and a human-readable development record.

## Grapher

This repository uses Grapher at `.grapher/knowledge.json`.

At the start of substantive work, inspect Grapher before re-deriving project knowledge. Record durable discoveries, decisions, evidence, and supersession through Grapher rather than relying on chat history alone.

Do not rewrite finalized historical evidence to make later conclusions look cleaner. Corrections should supersede or contradict earlier records while preserving them.

## Research ledgers

For substantive changes, update the appropriate file in `docs/`:

- `DEVELOPMENT_LEDGER.md` — chronological work, rationale, outcomes, commit references.
- `DECISION_LEDGER.md` — architectural decisions and alternatives.
- `EXPERIMENT_LEDGER.md` — hypotheses, procedures, observations, results.
- `FAILURE_LEDGER.md` — failures, unexpected behavior, and lessons.

Use UTC and local time when practical. Reference commit hashes, PRs, Grapher node IDs, and external evidence where available. Do not invent missing timestamps or provenance.

## Epistemic rule

Structured machine state and human commentary are distinct. Natural-language notes are useful for humans but must not silently become authoritative claims. As the typed Dreadnought protocol is implemented, machine-significant claims must migrate to normalized schema-backed records.
