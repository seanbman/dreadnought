# Agent instructions

## Index

- [Research discipline](#research-discipline)
- [CLI usage](#cli-usage)
- [Grapher](#grapher)
- [Research ledgers](#research-ledgers)
- [Epistemic rule](#epistemic-rule)
- [Appendix — Process flow](#appendix--process-flow)

## Research discipline

Dreadnought is being developed as both software and a research study. Preserve both machine-readable provenance and a human-readable development record. Follow [`docs/DIAGRAM_STANDARD.md`](docs/DIAGRAM_STANDARD.md) for documentation diagrams and commit provenance, and [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) for the root component/trust-boundary map. [Process map](#appendix--process-flow)

## CLI usage

Before invoking or scripting Dreadnought commands, read [`docs/CLI_USAGE.md`](docs/CLI_USAGE.md). It is the shared human/agent operational reference for command families, typed artifact locations, validation, protocol ingest, Project Arm dispatch, scratch requirements, adapter tokens, exit codes, and authority boundaries. The parser in [`src/dreadnought/cli.py`](src/dreadnought/cli.py) is executable authority for available flags; if `--help` differs from the guide, update the guide in the same change set. Do not infer that `init`, successful process exit, or protocol ingestion means acceptance or closure. [Process map](#appendix--process-flow)

## Grapher

This repository uses Grapher at `.grapher/knowledge.json`. At the start of work, inspect Grapher before re-deriving project knowledge. Every repository change set must update `.grapher/knowledge.json` and append `.grapher/history.jsonl`; CI rejects pull requests and direct `main` changes that do not satisfy both requirements. Grapher maintenance is therefore part of the change path, not optional cleanup. Record durable discoveries, decisions, evidence, and supersession through Grapher rather than relying on chat history alone. Do not rewrite finalized historical evidence to make later conclusions look cleaner. [Process map](#appendix--process-flow)

## Research ledgers

For substantive changes, update the appropriate file in `docs/`: `DEVELOPMENT_LEDGER.md`, `DECISION_LEDGER.md`, `EXPERIMENT_LEDGER.md`, `FAILURE_LEDGER.md`, and any specialized ledger listed in [`docs/INDEX.md`](docs/INDEX.md). New durable Markdown must be indexed, contain its own index, and include a provenance-bearing Mermaid process-flow appendix. Architecture-bearing documents must also include an architecture diagram linked to the root architecture. Process nodes representing implementation must identify concrete `code:` paths in addition to `inception:` and `current:` hashes. Use UTC and local time when practical. Reference commit hashes, PRs, Grapher node IDs, and external evidence where available. Do not invent missing timestamps or provenance. [Process map](#appendix--process-flow)

## Epistemic rule

Structured machine state and human commentary are distinct. Natural-language notes are useful for humans but must not silently become authoritative claims. Machine-significant claims must use normalized schema-backed records. [Process map](#appendix--process-flow)

## Appendix — Process flow

```mermaid
flowchart LR
    I["Inspect project knowledge\ncode: src/dreadnought/grapher.py\ninception: 96725840db44eef1d982b32376c69be3050cba3d\ncurrent: 27e69a59ebdc5c0a8d8cdf64dda86e50516bf12d"] --> W["Use documented CLI contract\ncode: src/dreadnought/cli.py\ninception: 2ddda47a622cc66b90e4a5ec65ea09262e002644\ncurrent: 27e69a59ebdc5c0a8d8cdf64dda86e50516bf12d"]
    W --> P["Typed protocol / evidence\ncode: src/dreadnought/protocol.py; src/dreadnought/verify.py\ninception: d6692863d9d43372f3fffc7b5c6fb821b6dafee1\ncurrent: 27e69a59ebdc5c0a8d8cdf64dda86e50516bf12d"]
    P --> G["Canonical Grapher write\ncode: src/dreadnought/grapher.py\ninception: 4630ac84da52677b343e7a3737844da683b25202\ncurrent: 27e69a59ebdc5c0a8d8cdf64dda86e50516bf12d"]
    G --> D["Human ledger + indexed docs\ncode: tests/test_documentation.py\ninception: 96725840db44eef1d982b32376c69be3050cba3d\ncurrent: 27e69a59ebdc5c0a8d8cdf64dda86e50516bf12d"]
```

Commit references: [research substrate](https://github.com/seanbman/dreadnought/commit/96725840db44eef1d982b32376c69be3050cba3d), [mission/CLI contract](https://github.com/seanbman/dreadnought/commit/2ddda47a622cc66b90e4a5ec65ea09262e002644), [typed protocol](https://github.com/seanbman/dreadnought/commit/d6692863d9d43372f3fffc7b5c6fb821b6dafee1), [Grapher control plane](https://github.com/seanbman/dreadnought/commit/4630ac84da52677b343e7a3737844da683b25202), [current architecture snapshot](https://github.com/seanbman/dreadnought/commit/27e69a59ebdc5c0a8d8cdf64dda86e50516bf12d).
