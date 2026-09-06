# Decision Ledger

Architectural decisions are recorded here as decisions, not rewritten later as if they were inevitable. Superseded decisions remain in place with links to the replacing decision.

## D-0001 — Dreadnought is a new architecture

**Date:** 2026-09-06  
**Status:** current

**Decision:** Build Dreadnought as a new project informed by Agent Hub and Grapher rather than evolving Agent Hub in place.

**Rationale:** The emerging design has a materially different authority model: Dreadnought is intended to be a control plane, observer, verifier, capability broker, and protocol compiler. Keeping a clean repository boundary makes inherited assumptions explicit rather than accidental.

**Alternatives considered:** Rename/refactor Agent Hub; fork Agent Hub wholesale; continue adding governance features to Agent Hub.

## D-0002 — Separate machine protocol from human notes

**Date:** 2026-09-06  
**Status:** current

**Decision:** Machine-significant claims, observations, actions, requirements, risks, artifacts, and verdicts should become typed/schema-backed protocol records. Freeform natural language remains available for human-facing notes, rationale, handoffs, and review commentary.

**Rationale:** Deterministic verification requires claims whose semantics can be reduced to known predicates. Prose alone is ambiguous and expensive to normalize after the fact.

## D-0003 — Grapher is a Dreadnought subsystem, not the whole control plane

**Date:** 2026-09-06  
**Status:** proposed

**Decision:** Preserve Grapher as an independently usable evidence/provenance component while making Dreadnought its privileged control-plane client.

**Rationale:** This allows Dreadnought to record agent testimony and independent observer evidence without coupling orchestration, policy, storage, and graph semantics into one inseparable daemon.

**Open question:** The exact API boundary and write authority remain to be tested.

## D-0004 — Taxonomy grows through observed use

**Date:** 2026-09-06  
**Status:** current

**Decision:** Begin with a deliberately small protocol taxonomy and expand enums/schema through real runs and failure analysis.

**Rationale:** A large ontology invented before use is likely to encode assumptions that have not earned evidence.
