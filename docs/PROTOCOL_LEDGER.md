# Protocol Ledger

Human-readable research record for the Dreadnought machine protocol. This ledger tracks taxonomy choices, authority boundaries, schema revisions, and evidence from real use. Entries are not rewritten when later revisions supersede them.

## 2026-09-06 — P-0001: Initial typed protocol

**Time:** approximately 08:23 MDT / 14:23 UTC  
**Branch:** `feature/typed-agent-protocol`  
**Predecessor:** PR #3, squash merge `db2c89af7ffa2c803020739eec578f20bcf5850c`

### Hypothesis

Execution-relevant agent communication should enter Dreadnought as typed records rather than freeform prose. Human-facing prose remains available as `note`, but notes must have no automatic machine semantics.

### Initial record taxonomy

`claim`, `observation`, `action`, `artifact`, `requirement`, `risk`, `note`, and `verdict`.

This taxonomy is intentionally provisional. New kinds or enums should be added only when real work demonstrates that the existing vocabulary cannot represent a necessary distinction cleanly.

### Authority boundary

An agent may author claims and request/propose actions, but it may not author an authoritative `observation`. Observation is reserved to the Dreadnought observer perspective. Similarly, only the evaluation perspective may issue a `verdict` or mark a requirement `verified`.

This prevents an agent from converting self-report into system evidence merely by selecting a stronger record label.

### Claims

The first claim shape uses a structured `subject_ref` plus a bounded predicate enum: `exists`, `absent`, `equals`, `succeeds`, `fails`, `complete`, and `unchanged`. Evidence references may accompany the claim but do not make the agent the authority over that evidence.

### Verdicts

Initial verdict statuses are `supported`, `contradicted`, `partially_supported`, `unverifiable`, `not_yet_verified`, and `malformed`. Positive or contradictory evidence-bearing verdicts require explicit evidence references. `unverifiable`, `not_yet_verified`, and `malformed` may exist without evidence because they describe the verifier's inability to reach an evidence-backed truth judgment.

### Human notes

`note` is explicitly human-facing and requires `audience=human`. Notes are not to be parsed automatically into claims, requirements, or state transitions. If prose needs machine significance, it must be normalized into another protocol record first.

### Implementation references

- `42a90b2f072a3bfa3d42cce935ee354a55d51f3c` — initial protocol types and validation
- `4b698c5d71c32f40dea0c29cc60c929a533fc46c` — authority-boundary tests
- `b5201b5e9634887b33733422304e7562f1b5487d` — versioned JSON Schema

### Open questions

The current predicate set may be too generic or too small. Artifact and risk enums may also need refinement. We will not widen them pre-emptively; Project Arm runs should generate the evidence for revision.
