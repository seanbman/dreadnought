# Experiment Ledger

Experiments should state falsifiable hypotheses where possible. Agent opinions may propose tests; deterministic observations should determine machine verdicts when a suitable predicate exists.

## E-0001 — Typed protocol can make agent claims mechanically testable

**Date opened:** 2026-09-06  
**Status:** planned

**Hypothesis:** For common software-agent assertions such as test success, build success, file mutation scope, Git state, and artifact existence, a normalized claim schema can map the assertion to deterministic evidence without an LLM deciding truth.

**Initial procedure:** Implement a minimal claim taxonomy and verifiers for command exit status, filesystem state, hashes/diffs, and Git state. Run one real agent mission and compare its submitted claims with Dreadnought observations.

**Success criterion:** Dreadnought can classify supported/contradicted/unverified claims from authoritative observations while preserving the original agent claim.

## E-0002 — Authority mediation can make Grapher protocol difficult to bypass

**Date opened:** 2026-09-06  
**Status:** planned

**Hypothesis:** If authoritative mutations are owned by Dreadnought rather than the agent, Grapher recording can become a property of the mutation path instead of a voluntary agent behavior.

**Initial procedure:** Prototype a read-only canonical workspace plus writable scratch/overlay and require Dreadnought mediation for authoritative changes.

**Success criterion:** An agent lacking control-plane credentials cannot mutate canonical project state without traversing the recorded Dreadnought path.
