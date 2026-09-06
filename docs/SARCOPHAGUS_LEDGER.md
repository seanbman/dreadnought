# Sarcophagus Ledger

Human-readable research record for Dreadnought's execution-isolation boundary. This ledger records what the Sarcophagus actually enforces, what remains aspirational, and what fails during adversarial testing.

## 2026-09-06 — S-0001: First executable isolation boundary

- **Time:** approximately 08:45 MDT / 14:45 UTC
- **Status:** proposed implementation; CI pending
- **Scope:** Linux execution boundary
- **Hypothesis:** Dreadnought can make bypass materially harder by removing ordinary write and network authority from an agent process rather than relying on prompts or wrappers.
- **Backend:** Bubblewrap (`bwrap`) only in this prototype.
- **Default policy:** canonical workspace read-only; scratch directory writable and outside the workspace; network namespace isolated; environment allowlisted; process dies with parent.
- **Failure behavior:** if Bubblewrap is unavailable, Dreadnought refuses execution. There is deliberately no unsandboxed fallback.
- **Writable-path rule:** explicitly writable paths may be mounted only outside the canonical workspace.
- **Not yet enforced:** brokered network access, seccomp syscall policy, cgroups/resource budgets, Landlock/AppArmor profiles, Git credential brokerage, authoritative mutation broker, scratch-to-workspace promotion, and Project Arm dispatch.
- **Security limitation:** Bubblewrap configuration is an initial Linux containment mechanism, not a claim of a complete security boundary. The implementation must be adversarially tested on the target host before agents are treated as untrusted processes.
- **Research question:** can this boundary preserve useful coding-agent freedom while making authoritative workspace mutation an explicit Dreadnought-mediated operation?
