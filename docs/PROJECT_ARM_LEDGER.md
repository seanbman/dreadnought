# Project Arm Ledger

Human-readable research record for dispatching compartmentalized Orders to subordinate execution arms.

## 2026-09-06 — PA-0001: First dispatcher substrate

- **Time:** approximately 17:08 MDT / 23:08 UTC
- **Status:** implementation under test
- **Predecessor:** Sarcophagus PR #8, squash merge `ce853e50706259b32585e7311b1d74638cb2bda5`
- **Objective:** establish one-Order/one-Project-Arm dispatch through a provider-neutral command adapter without giving the subordinate project-wide strategic context.
- **Order transport:** Dreadnought serializes the normalized Order into the external scratch area, not the canonical workspace.
- **Execution:** the adapter command is executed through Sarcophagus rather than directly on the host.
- **Observation:** Dreadnought records process exit code, stdout, stderr, adapter identity, and Order reference as an observer-perspective protocol record and writes it through the Grapher control plane.
- **Adapter model:** the first adapter is intentionally provider-neutral. Static command arguments may contain explicit `{order}`, `{scratch}`, `{workspace}`, `{project_arm}`, and `{objective}` tokens. Vendor-specific adapters should refine this contract rather than bypass it.
- **Not yet claimed:** no Codex/Cursor/local-model adapter has been validated on a real workspace yet; no agent-authored structured return channel exists yet; no scratch-to-canonical mutation broker exists yet.
- **Research question:** does the adapter boundary preserve enough provider flexibility to run real coding agents while keeping Orders, authority, observation, and canonical writes under Dreadnought control?

## Process note — accidental PR #9

A no-op draft PR #9 was opened accidentally during transition from the Sarcophagus merge and immediately closed without merge. It carried no new branch state and is retained in GitHub history rather than hidden or repurposed.
