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

## 2026-09-06 — Mission schema and CLI skeleton

**Time:** approximately 07:41 MDT / 13:41 UTC  
**Branch:** `feature/mission-schema-cli`  
**Predecessor merge:** PR #1, merge commit `96725840db44eef1d982b32376c69be3050cba3d`

### Hypothesis

A Dreadnought mission should exist as a typed artifact before any agent is invoked. Human natural-language intent may be preserved as source input, but execution-relevant state should be represented by explicit fields and bounded enums rather than inferred repeatedly from prose.

### Implementation

The first executable substrate is intentionally small and uses the Python standard library. It adds:

- an installable `dreadnought` CLI entry point;
- a mission model with lifecycle, source, access, and capability enums;
- `dreadnought mission init`, `validate`, and `show` commands;
- a versioned JSON Schema at `schemas/mission.schema.json`;
- baseline tests for draft validation and serialization round trips.

Relevant implementation commits include `11bfb29754008a8756b7d58efcf62a939bd9876d`, `a0845201208198460c184e151a65cb2a8bf2ea8e`, `2054c23cbd3cfdeac62aa6c0dad5787e73ed8d6e`, `eba4b07292ed7cc8843d69c9e4dd1edb14230ccb`, and `f243fd92b1b62419ff0352fee88c0b8c01ef9fd3`.

### Deliberate limitations

This is not yet an agent launcher, natural-language semantic normalizer, policy engine, or Grapher write path. Capability fields currently describe requested mission configuration; they do not yet grant authority. That separation is deliberate so the next experiments can distinguish desired configuration from effective enforced capability.

### What we are testing

Whether a minimal mission contract is expressive enough to carry real work into the upcoming typed protocol without prematurely inventing a large ontology. Any field that repeatedly fails to represent real missions should become evidence for schema revision rather than being patched with opaque prose.
