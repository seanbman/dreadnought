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

## D-0005 — Mission configuration is not authority

**Date:** 2026-09-06  
**Status:** current

**Decision:** Mission documents may express requested sources, access modes, and capabilities, but those fields do not themselves grant privileges. Effective authority must later be derived by Dreadnought from mission intent intersected with control-plane and workspace policy.

**Rationale:** A natural-language directive or editable mission file must never be able to weaken the enforcement boundary merely by requesting broader access. Keeping desired configuration separate from effective capabilities also gives the observer layer something concrete to compare against actual execution.

**Implementation reference:** branch `feature/mission-schema-cli`, beginning with commit `11bfb29754008a8756b7d58efcf62a939bd9876d`.

## D-0006 — Doctrine precedes execution orders

**Date:** 2026-09-06  
**Time:** 07:54 MDT / 13:54 UTC  
**Status:** current

**Decision:** Freeform human input and supporting artifacts are normalized into a versioned Doctrine document before Dreadnought decomposes work into PR-sized Operations. Doctrine is the authoritative interpretation layer between human intent and execution planning.

**Doctrine responsibilities:** preserve source provenance; distinguish requirements from preferences and unresolved questions; define acceptance conditions; record constraints and priorities; and define where creative agency is encouraged, bounded, approval-gated, or prohibited.

**Rationale:** Agents should not directly consume undifferentiated project-wide human context as their authoritative order. A normalization boundary reduces ambiguity and contamination while retaining traceability back to the original source material.

## D-0007 — Use Task Group and Project Arm nomenclature

**Date:** 2026-09-06  
**Time:** 07:54 MDT / 13:54 UTC  
**Status:** current

**Decision:** Use the working hierarchy `Dreadnought → Task Group → Project Arm → Agent`. A Campaign Plan decomposes Doctrine into Operations; a Project Arm receives a compartmentalized Order for an Operation and may contain one agent initially, with subordinate orchestration deferred until evidence justifies it.

**Rationale:** `Project Arm` describes an execution branch extending from the control plane without implying that the subordinate has project-wide strategic authority. `Task Group` provides a future grouping boundary for related Project Arms without requiring multi-agent orchestration in the first implementation.

## D-0008 — Creative agency is explicit and scoped

**Date:** 2026-09-06  
**Time:** 07:54 MDT / 13:54 UTC  
**Status:** current

**Decision:** Orders carry a structured creative-authority envelope. Dreadnought should specify dimensions where an agent has high, medium, low, approval-required, or prohibited discretion rather than treating creativity as either unrestricted or absent.

**Rationale:** Development benefits from agent initiative in implementation, naming, design, debugging, and exploration, but freedom should not silently extend into architecture, destructive state changes, security policy, or other authority-sensitive decisions. Explicit scope minimizes context leakage and overreach while preserving useful agency.

## D-0009 — Project Arms receive least necessary strategic context

**Date:** 2026-09-06  
**Time:** 07:55 MDT / 13:55 UTC  
**Status:** current

**Decision:** An Order is a compartmentalized execution package, not a copy of the complete project context. Dreadnought retains the strategic picture and supplies a Project Arm only the Doctrine fragments, sources, graph references, dependencies, acceptance criteria, requested capabilities, and creative authority needed for its Operation.

**Rationale:** Context minimization reduces cross-agent contamination, accidental authority expansion, and irrelevant prompt load while preserving enough local information for useful initiative. Additional context may be requested or granted explicitly when an Operation demonstrates that it is needed.

## D-0010 — Dreadnought owns canonical Grapher protocol writes

**Date:** 2026-09-06  
**Time:** approximately 08:26 MDT / 14:26 UTC  
**Status:** current

**Decision:** Project Arms and agents submit typed `ProtocolRecord` objects to Dreadnought; the control plane validates them and is the only software component that projects those records into canonical `.grapher/knowledge.json` and `.grapher/history.jsonl` state.

**Rationale:** Actor identity and write authority are distinct. An agent-authored claim must remain attributable to that agent while the canonical write itself is attributable to `dreadnought:control-plane`. This prevents an agent from promoting its own testimony into observer/evaluation authority merely by editing Grapher directly.

**Current limitation:** This PR establishes the software boundary, duplicate rejection, validation-before-mutation, and provenance split. The later Sarcophagus milestone must enforce the same boundary at the OS/filesystem level so direct Grapher mutation is not merely discouraged but denied.

## D-0011 — Verification is deterministic and verifier-specific

**Date:** 2026-09-06  
**Time:** approximately 08:32 MDT / 14:32 UTC  
**Status:** current

**Decision:** Dreadnought evaluates claims only through named deterministic verifiers whose inputs and observations are explicit. The first registry covers filesystem existence/absence, SHA-256 file hashes, and command exit status. Unknown or unsupported verification requests resolve to `unverifiable` rather than being guessed from prose.

**Rationale:** A verdict must be reproducible from observable evidence. Separating verifier implementations from agent claims prevents an agent from defining its own proof standard after execution and gives later Grapher records a concrete evidence source.

**Boundary:** Command verification records exit code and captured output but does not yet provide sandboxing or authority isolation. Sarcophagus remains responsible for constraining what a verifier process is allowed to execute.

## D-0012 — Agent results are testimony, never observer authority

**Date:** 2026-09-06  
**Time:** approximately 17:12 MDT / 23:12 UTC  
**Status:** current

**Decision:** External agents may return typed protocol records only through a scratch-resident result channel. Records accepted from that channel must use the `agent` perspective and may not use observer- or evaluation-reserved kinds. Dreadnought validates and rebinds them to the dispatched Order before canonical Grapher ingestion.

**Rationale:** Structured output is useful only if its epistemic class remains intact. A compromised or mistaken agent must not be able to emit an `observation` or `verdict` record and thereby promote testimony into evidence or evaluation authority.

**Boundary:** The channel validates protocol identity and Order association. It does not yet prove which operating-system process wrote a result file; stronger process identity and signed/session-bound records remain future hardening work.
