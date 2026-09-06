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

## 2026-09-06 — Doctrine, Campaign Plan, and Project Arm Orders

**Time:** approximately 07:55 MDT / 13:55 UTC  
**Branch:** `feature/doctrine-campaign-orders`  
**Predecessor merge:** PR #2, squash merge commit `2ddda47a622cc66b90e4a5ec65ea09262e002644`

### Hypothesis

A mission record alone is too close to raw human input to serve as an execution order. Dreadnought needs an explicit interpretation layer that preserves source provenance, resolves intent into structured constraints and acceptance conditions, and then exposes only operation-relevant context to subordinate execution arms.

### Implementation under test

The branch introduces three distinct artifacts:

- `Doctrine`: the versioned authoritative interpretation of human intent, including requirements, constraints, priorities, acceptance criteria, unresolved questions, source references, notes, and a bounded creative-authority envelope.
- `CampaignPlan`: a project-level decomposition of Doctrine into named Operations with dependencies, scope, and required outcomes under a Task Group.
- `Order`: the compartmentalized package issued to one Project Arm, carrying Doctrine/Campaign/Operation references, bounded scope, acceptance criteria, requested capabilities, relevant sources and requirements, and explicit creative latitude.

Initial implementation commits include `68838280131c15ab0ea3d6e37b7235af4469e9e4`, `d91daef001a241121b1164b3c53812782797d475`, `28e99746581cf6bcd77650f50b78f2ee8c0723da`, `191a8432f9336af8ec7cb87558febabe29725fc5`, and `c6212bc68f250b5c7b5e80ee52034240896a1f53`.

### Deliberate limitations

This PR does not claim to solve semantic normalization from arbitrary human prose, automatic PR creation, source ingestion, or policy enforcement. It establishes the typed boundary those later mechanisms must target. The creative-authority enum is intentionally small and provisional; use in real projects will determine whether its categories survive.

### Research question

Can Doctrine → Campaign Plan → Order provide enough context for useful implementation while materially reducing context leakage and unauthorized strategic decision-making by Project Arms?
