# Dreadnought research record

These documents are the human-readable counterpart to `.grapher/`. They are deliberately kept in version control so the evolution of the architecture can be studied against dates, commits, PRs, experiments, and machine evidence.

Use [`INDEX.md`](INDEX.md) as the canonical documentation map. Any new durable Markdown document under `docs/` should be added there in the same PR.

The ledgers are not polished retrospective documentation. They are a contemporaneous research notebook. Preserve wrong turns, superseded hypotheses, failed experiments, and uncertainty when those are part of what actually happened.

## Core documents

- [`INDEX.md`](INDEX.md) — canonical map of all human-readable project documents and their authority.
- [`ARCHITECTURE_CHARTER.md`](ARCHITECTURE_CHARTER.md) — current architectural principles and system boundaries.
- [`ROADMAP.md`](ROADMAP.md) — active PR sequence, completed milestones, and deferred work.

## Ledgers

- [`DEVELOPMENT_LEDGER.md`](DEVELOPMENT_LEDGER.md) — chronological project record.
- [`DECISION_LEDGER.md`](DECISION_LEDGER.md) — architectural decisions and alternatives.
- [`EXPERIMENT_LEDGER.md`](EXPERIMENT_LEDGER.md) — testable hypotheses and results.
- [`FAILURE_LEDGER.md`](FAILURE_LEDGER.md) — failures and lessons without rewriting history.
- [`PROTOCOL_LEDGER.md`](PROTOCOL_LEDGER.md) — typed protocol taxonomy, authority boundaries, and protocol evolution.

## Entry discipline

Prefer an entry containing: timestamp, scope, rationale or hypothesis, work performed, observed outcome, evidence references, commit/PR references, and follow-up. If a field is unknown, say so rather than reconstructing it from memory.

Historical ledger entries are append-oriented. If a later decision supersedes an earlier one, record the new decision and link the supersession rather than rewriting the old entry.
