# Project Arm Ledger

Human-readable research record for dispatching compartmentalized Orders to subordinate execution arms.

## 2026-09-06 — PA-0001: First dispatcher substrate

- **Time:** approximately 17:08 MDT / 23:08 UTC
- **Status:** merged in PR #10
- **Predecessor:** Sarcophagus PR #8, squash merge `ce853e50706259b32585e7311b1d74638cb2bda5`
- **Objective:** establish one-Order/one-Project-Arm dispatch through a provider-neutral command adapter without giving the subordinate project-wide strategic context.
- **Order transport:** Dreadnought serializes the normalized Order into the external scratch area, not the canonical workspace.
- **Execution:** the adapter command is executed through Sarcophagus rather than directly on the host.
- **Observation:** Dreadnought records process exit code, stdout, stderr, adapter identity, and Order reference as an observer-perspective protocol record and writes it through the Grapher control plane.
- **Adapter model:** the first adapter is intentionally provider-neutral. Static command arguments may contain explicit `{order}`, `{scratch}`, `{workspace}`, `{project_arm}`, and `{objective}` tokens. Vendor-specific adapters should refine this contract rather than bypass it.
- **Verification:** GitHub Actions run `34066144031` completed successfully before merge.
- **Merge:** squash merge `6c049f77981917d716722096674976c1ea5c4261`.
- **Not yet claimed:** no Codex/Cursor/local-model adapter has been validated on a real workspace yet; no scratch-to-canonical mutation broker exists yet.
- **Research question:** does the adapter boundary preserve enough provider flexibility to run real coding agents while keeping Orders, authority, observation, and canonical writes under Dreadnought control?

## 2026-09-06 — PA-0002: Typed agent result channel

- **Time:** approximately 17:12 MDT / 23:12 UTC
- **Status:** implementation under test
- **Objective:** let an external agent report structured claims and artifacts without allowing it to create observer or evaluation authority.
- **Transport:** each dispatch reserves a scratch-resident JSONL result path and exposes it to the adapter through the explicit `{result}` token.
- **Accepted records:** agent-perspective claim, action, artifact, requirement, risk, and note records.
- **Rejected records:** any non-agent perspective and all observer/evaluation-reserved kinds.
- **Order binding:** records with no `order_ref` are bound by Dreadnought to the active Order; records naming a different Order are rejected.
- **Canonical write:** validated agent records are written through `GrapherControlPlane`, preserving agent authorship while Dreadnought remains the writer.
- **Research question:** can this channel cleanly separate agent testimony from Dreadnought observations during a real Project Arm run without requiring freeform result parsing?

## Process note — accidental PR #9

A no-op draft PR #9 was opened accidentally during transition from the Sarcophagus merge and immediately closed without merge. It carried no new branch state and is retained in GitHub history rather than hidden or repurposed.
