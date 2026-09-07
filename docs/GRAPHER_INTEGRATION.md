# Dreadnought / Grapher Integration

## Index

- [Authority model](#authority-model)
- [Compatibility baseline](#compatibility-baseline)
- [Configuration flow](#configuration-flow)
- [Read brokering](#read-brokering)
- [Write mediation](#write-mediation)
- [Architecture](#architecture)
- [Appendix — Process flow](#appendix--process-flow)

## Authority model

Dreadnought encapsulates Grapher as its durable cognitive substrate. Grapher remains independently operable, but inside a Dreadnought-controlled workspace **Dreadnought is the sole Grapher writer**.

Project Arms inside Sarcophagus do not mutate Grapher. They submit typed `ProtocolRecord` testimony to the Dreadnought control plane. Dreadnought validates authority and protocol semantics, projects the record into a Dreadnought-specific Grapher type, and calls `grapher.integrations.embedded`. Grapher then owns canonical persistence, truth policy, semantic integrity, status transitions, provenance history, and rollback.

Dreadnought may also create its own observations. Agent testimony and Dreadnought observations remain distinguishable through protocol perspective, actor metadata, and provenance.

## Compatibility baseline

The current public beta pairing is **Dreadnought v0.2.0b1 → Grapher v0.7.0b1**. Dreadnought's package metadata targets the published `v0.7.0b1` Grapher release ref. Grapher v0.6.1 remains the historical first compatibility baseline that formalized the host-agnostic embedded/brokering interface; v0.7.0b1 carries that boundary forward while adding Linux distribution and release-aware update discovery.

Check a workspace with:

```bash
dreadnought grapher doctor --root /path/to/project
```

For installation/version behavior see [`INSTALLATION_AND_UPDATES.md`](INSTALLATION_AND_UPDATES.md).

## Configuration flow

1. Install Dreadnought; its dependency installs the matched Grapher line.
2. Initialize a new controlled workspace with `dreadnought grapher init --root <project>`.
3. Dreadnought creates Grapher and materializes the required Dreadnought projection policy.
4. `.grapher/config.json` registers the `dreadnought_*` node types and requires explicit truth status.
5. Mission/order/session context supplies scope and actor provenance.
6. `ProtocolRecord.validate()` is the admission gate.
7. `GrapherControlPlane` projects the complete record losslessly into `meta.protocol` and a `dreadnought_*` node type.
8. Grapher's embedded API performs canonical mutation and structured history.
9. Git governance evidence is published under `.grapher/shared/`; local runtime graph/history are not the Git publication contract.

Initialization fails closed if an existing graph is present rather than overwriting it.

## Read brokering

```bash
dreadnought grapher query "known failures" --root . --limit 8
dreadnought grapher query "known failures" --root . --mission <mission-id> --limit 8
dreadnought grapher get <node-id> --root .
```

Programmatic callers use `GrapherControlPlane.query()` and `GrapherControlPlane.get()`. Project Arms should receive relevant Grapher context through this broker so Dreadnought controls mission scope and context volume without exposing mutation authority.

## Write mediation

```text
Project Arm testimony or Dreadnought observation
→ ProtocolRecord
→ Dreadnought validation/admission
→ Dreadnought protocol projection
→ grapher.integrations.embedded
→ Grapher canonical mutation
→ local graph + structured history
```

The original protocol payload is preserved losslessly in node metadata. Dreadnought uses `dreadnought_*` node types so host protocol semantics are not confused with Grapher's strict native semantic-entry contracts. There is intentionally no general-purpose subordinate `grapher add` path through Dreadnought.

## Architecture

```mermaid
flowchart LR
    A["Project Arm / Sarcophagus\ninception: f395fb7\ncurrent beta: cae9fc9"] -->|typed testimony| D["Dreadnought Control Plane\ninception: 4630ac8\ncurrent beta: cae9fc9"]
    A -->|context request| R["Dreadnought read broker\ncode: src/dreadnought/grapher.py; cli.py\ninception: e5f7fd3\ncurrent beta: cae9fc9"]
    R --> E["Grapher embedded API\ninception: b3729dad\ncurrent beta: 13a1f2ca"]
    D -->|authorized projection only| E
    E --> G["Grapher canonical mutation/history\ninception compatibility: d410cd5\ncurrent beta: 13a1f2ca"]
    G --> B[("Durable brain state")]
```

## Appendix — Process flow

```mermaid
flowchart TD
    I["Initialize managed brain\ncode: src/dreadnought/grapher.py; cli.py\ninception: e4c6caf\ncurrent beta: cae9fc9"] --> C["Compatibility doctor\ncode: src/dreadnought/grapher.py\ninception: e5f7fd3\ncurrent beta: cae9fc9"]
    C --> P["ProtocolRecord produced\ncode: src/dreadnought/protocol.py\ninception: 4630ac8\ncurrent beta: cae9fc9"]
    P --> V["Validate admission + project\ncode: src/dreadnought/grapher.py\ninception: 4630ac8\ncurrent beta: cae9fc9"]
    V --> E["Embedded Grapher API\ncode: grapher/integrations/embedded.py\ninception: b3729dad\ncurrent beta: 13a1f2ca"]
    E --> M["Canonical mutation + history\ncode: Grapher store/graph paths\ninception compatibility: d410cd5\ncurrent beta: 13a1f2ca"]
    M --> S["validate → audit → publish → .grapher/shared/\ninception: Grapher transport\ncurrent beta: 13a1f2ca"]
```

The central invariant is intentionally asymmetric: **reads may be brokered to subordinate agents, but all mutations are mediated by Dreadnought.**
