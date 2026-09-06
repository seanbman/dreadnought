# Development Ledger

Chronological record of Dreadnought's development. Entries should describe what was actually done and why, with evidence references where possible.

## 2026-09-06 — Project founding

**Time:** 07:31 MDT / 13:31 UTC  
**Repository:** `seanbman/dreadnought`  
**Founding commit:** `3bea73dd2ca73199b86b49998e049fb0f30c454f`

### Context

Dreadnought begins as a new architecture rather than a rename or direct continuation of Agent Hub. Agent Hub and Grapher are treated as experimental predecessors and evidence sources. The immediate design direction is a control plane that normalizes human mission directives, constrains agent capabilities, independently observes execution, and compares structured agent claims with deterministic evidence.

### Research-record decision

Development will maintain two complementary records:

1. `.grapher/` for machine-readable knowledge, provenance, relationships, and eventually normalized protocol records.
2. `docs/` ledgers for human-readable rationale, experiments, failures, and architectural evolution.

The human record is intentionally commit-addressable so later conclusions can be compared with what was believed at the time.

### Initial next step

Bootstrap the repository with the research ledgers, architecture charter, Grapher root, and the first PR roadmap before implementing orchestration code.
