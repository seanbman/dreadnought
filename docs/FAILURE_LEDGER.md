# Failure Ledger

Failures are retained because they are design evidence. Do not clean them out of the narrative when later work succeeds.

## F-0001 — Agent Hub orchestration contamination

**Date recorded:** 2026-09-06  
**Historical source period:** prior Agent Hub / Dreadnought case-study work

**Observed problem:** Earlier orchestration work demonstrated that an orchestration layer can introduce assumptions, procedural rules, or closure behavior that are not grounded in authoritative project evidence. In at least one case-study workflow, role-boundary interference contaminated the evidence needed to establish authentic agent acceptance/closure.

**Lesson carried forward:** Dreadnought must distinguish user authority, mission protocol, agent testimony, observer evidence, verification, acceptance, and closure rather than allowing conversational inference to collapse them together.

**Evidence status:** Historical evidence exists in the Agent Hub and case-study source material. It should be imported and cited explicitly in a later evidence-ingestion PR rather than expanded here from memory.

## F-0002 — Voluntary Grapher use is not enforcement

**Date recorded:** 2026-09-06

**Observed problem:** An instruction telling an agent to record its work cannot prevent direct filesystem, Git, or network actions that bypass the recorder when the agent has equivalent authority.

**Lesson carried forward:** Grapher compliance must eventually be enforced by the control-plane capability boundary, not prompt wording or CLI etiquette.
