# Project Arm Ledger

## Index

- [Purpose](#purpose)
- [PA-0001 — First dispatcher substrate](#2026-09-06--pa-0001-first-dispatcher-substrate)
- [PA-0002 — Typed agent result channel](#2026-09-06--pa-0002-typed-agent-result-channel)
- [Process note — accidental PR #9](#process-note--accidental-pr-9)
- [Architecture diagram](#architecture-diagram)
- [Appendix — Process flow](#appendix--process-flow)

## Purpose

Human-readable research record for dispatching compartmentalized Orders to subordinate execution arms. Root context: [`ARCHITECTURE.md`](ARCHITECTURE.md). [Process map](#appendix--process-flow)

## 2026-09-06 — PA-0001: First dispatcher substrate

- **Time:** approximately 17:08 MDT / 23:08 UTC
- **Status:** merged in PR #10
- **Predecessor:** Sarcophagus PR #8, squash merge `ce853e50706259b32585e7311b1d74638cb2bda5`
- **Objective:** establish one-Order/one-Project-Arm dispatch through a provider-neutral command adapter without giving the subordinate project-wide strategic context.
- **Order transport:** Dreadnought serializes the normalized Order into external scratch, not the canonical workspace.
- **Execution:** the adapter command is executed through Sarcophagus rather than directly on the host.
- **Observation:** Dreadnought records process exit code, stdout, stderr, adapter identity, and Order reference as observer evidence through Grapher.
- **Verification:** GitHub Actions run `34066144031` completed successfully before merge.
- **Merge:** squash merge `6c049f77981917d716722096674976c1ea5c4261`.
- **Not yet claimed:** no Codex/Cursor/local-model adapter has been validated on a real workspace yet; no scratch-to-canonical mutation broker exists yet.

[Process map](#appendix--process-flow)

## 2026-09-06 — PA-0002: Typed agent result channel

- **Time:** approximately 17:12 MDT / 23:12 UTC
- **Status:** merged in PR #11; CI passed
- **Objective:** let an external agent report structured claims and artifacts without allowing it to create observer or evaluation authority.
- **Transport:** each dispatch reserves a scratch-resident JSONL result path exposed through `{result}`.
- **Accepted records:** agent-perspective claim, action, artifact, requirement, risk, and note records.
- **Rejected records:** any non-agent perspective and all observer/evaluation-reserved kinds.
- **Order binding:** records without `order_ref` are bound to the active Order; records naming a different Order are rejected.
- **Canonical write:** validated agent records are written through `GrapherControlPlane`, preserving agent authorship while Dreadnought remains the writer.
- **Merge:** squash merge `f8f40d1d072d0c37a1ba4d63c430a234339c1a54`.

[Process map](#appendix--process-flow)

## Process note — accidental PR #9

A no-op draft PR #9 was opened accidentally during transition from the Sarcophagus merge and immediately closed without merge. It carried no new branch state and is retained in GitHub history rather than hidden or repurposed.

## Architecture diagram

```mermaid
flowchart TB
    ORD["Order model\ncode: src/dreadnought/order.py"] --> DISP["ProjectArmDispatcher\ncode: src/dreadnought/dispatch.py"]
    DISP --> AD["AgentAdapter / CommandAgentAdapter\ncode: src/dreadnought/agent.py"]
    DISP --> SARC["Sarcophagus\ncode: src/dreadnought/sarcophagus.py"]
    SARC --> EXT["External agent process\ncode: src/dreadnought/agent.py"]
    EXT --> RESULT["AgentResultChannel\ncode: src/dreadnought/result_channel.py"]
    DISP --> OBS["Observer ProtocolRecord\ncode: src/dreadnought/dispatch.py; src/dreadnought/protocol.py"]
    RESULT --> GRAPH["GrapherControlPlane\ncode: src/dreadnought/grapher.py"]
    OBS --> GRAPH
```

## Appendix — Process flow

```mermaid
flowchart LR
    O["Compartmentalized Order\ncode: src/dreadnought/order.py\ninception: db2c89af7ffa2c803020739eec578f20bcf5850c\ncurrent: 437b3c512aefbc40d591c3322188c6d2732e31b2"] --> D["Project Arm dispatcher\ncode: src/dreadnought/dispatch.py\ninception: 6c049f77981917d716722096674976c1ea5c4261\ncurrent: 437b3c512aefbc40d591c3322188c6d2732e31b2"]
    D --> S["Sarcophagus + scratch\ncode: src/dreadnought/sarcophagus.py\ninception: ce853e50706259b32585e7311b1d74638cb2bda5\ncurrent: 437b3c512aefbc40d591c3322188c6d2732e31b2"]
    S --> A["External agent\ncode: src/dreadnought/agent.py\ninception: 6c049f77981917d716722096674976c1ea5c4261\ncurrent: 437b3c512aefbc40d591c3322188c6d2732e31b2"]
    A --> R["Typed result channel\ncode: src/dreadnought/result_channel.py\ninception: f8f40d1d072d0c37a1ba4d63c430a234339c1a54\ncurrent: 437b3c512aefbc40d591c3322188c6d2732e31b2"]
    D --> E["Observer evidence\ncode: src/dreadnought/dispatch.py; src/dreadnought/protocol.py\ninception: 6c049f77981917d716722096674976c1ea5c4261\ncurrent: 437b3c512aefbc40d591c3322188c6d2732e31b2"]
    R --> G["Grapher canonical write\ncode: src/dreadnought/grapher.py\ninception: 4630ac84da52677b343e7a3737844da683b25202\ncurrent: 437b3c512aefbc40d591c3322188c6d2732e31b2"]
    E --> G
```

Commit references: [Doctrine/Orders](https://github.com/seanbman/dreadnought/commit/db2c89af7ffa2c803020739eec578f20bcf5850c), [Grapher](https://github.com/seanbman/dreadnought/commit/4630ac84da52677b343e7a3737844da683b25202), [Sarcophagus](https://github.com/seanbman/dreadnought/commit/ce853e50706259b32585e7311b1d74638cb2bda5), [dispatch](https://github.com/seanbman/dreadnought/commit/6c049f77981917d716722096674976c1ea5c4261), [typed result channel](https://github.com/seanbman/dreadnought/commit/f8f40d1d072d0c37a1ba4d63c430a234339c1a54), [documentation baseline](https://github.com/seanbman/dreadnought/commit/437b3c512aefbc40d591c3322188c6d2732e31b2).
