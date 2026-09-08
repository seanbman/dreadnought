from __future__ import annotations

import argparse
import json
from pathlib import Path
import shlex
import sys

from .bootstrap import (
    _choose_project_root,
    _launch_primary_agent,
    _project_ref,
    bootstrap_workspace,
    render_instructions,
)
from .config import load_config
from .grapher import GrapherControlPlane
from .kernel import PrimaryKernel
from .mission import CapabilitySet, Mission
from .project_policy import project_policy, set_project_policy
from .usage import TokenUsageLedger


def _with_max_minions(mission: Mission, max_minions: int | None) -> Mission:
    caps = mission.capabilities
    mission.capabilities = CapabilitySet(
        canonical_workspace=caps.canonical_workspace,
        scratch_write=caps.scratch_write,
        git_inspect=caps.git_inspect,
        git_propose_commit=caps.git_propose_commit,
        git_push=caps.git_push,
        network=caps.network,
        shell=caps.shell,
        max_minions=max_minions,
    )
    errors = mission.validate()
    if errors:
        raise ValueError("invalid bootstrap mission: " + "; ".join(errors))
    return mission


def _kernel_instructions(base: str, max_minions: int | None) -> str:
    rendered_limit = "unlimited" if max_minions is None else str(max_minions)
    return base.rstrip() + f"""

## Kernel boundary

- The primary Dreadnought agent runs inside the Dreadnought kernel. The canonical workspace and managed project are read-only inside that process.
- Primary-agent project mutation is prohibited by policy and by the Bubblewrap filesystem boundary; instructions are not the security boundary.
- The primary may inspect canonical project state, but all canonical mutation must occur in the host-side Dreadnought control plane.
- The primary communicates with minions only through `dreadnought control commission`. Direct minion output has no authority and is never admitted as canonical evidence unless the control plane broker records it.
- The primary receives writable scratch through `$DREADNOUGHT_SCRATCH` and broker access through `$DREADNOUGHT_CONTROL_SOCKET`.
- GitHub/SSH credential channels are removed from the primary kernel environment. Git push remains outside primary-agent authority.
- Project max concurrent minions: `{rendered_limit}`.
- `dreadnought control usage` returns current measured token totals plus active/unmetered coverage whenever exact provider token counts are unavailable.
""" + "\n"


def _parse_max_minions(value: str | None) -> int | None:
    if value is None or not str(value).strip():
        return None
    parsed = int(value)
    if parsed < 0:
        raise ValueError("max_minions must be >= 0")
    return parsed


def run_bootstrap_cli(argv: list[str], *, prog: str = "dreadnought initialize") -> int:
    parser = argparse.ArgumentParser(prog=prog, description="Initialize/adopt a Dreadnought workspace with kernel-enforced project boundaries")
    parser.add_argument("brief", nargs="?", help="bootstrap directive / human intent")
    parser.add_argument("--directive", help="bootstrap directive (alternative to positional brief)")
    parser.add_argument("--objective")
    parser.add_argument("--requirement", action="append", default=[])
    parser.add_argument("--root", default=".")
    parser.add_argument("--project-id")
    parser.add_argument("--project-root")
    parser.add_argument("--max-minions", type=int, help="maximum concurrent minions for this project; omit for no numerical cap")
    parser.add_argument("--actor", default="human:user")
    parser.add_argument("--agent-type")
    parser.add_argument("--agent-executable")
    parser.add_argument("--agent-arg", action="append", default=[])
    parser.add_argument("--chat", action="store_true")
    parser.add_argument("--non-interactive", action="store_true")
    args = parser.parse_args(argv)

    root = Path(args.root).resolve()
    root.mkdir(parents=True, exist_ok=True)
    interactive = not args.non_interactive and sys.stdin.isatty() and sys.stdout.isatty()
    directive = (args.directive or args.brief or "").strip()
    objective = (args.objective or "").strip()
    project_id = args.project_id
    project_root = args.project_root
    max_minions = args.max_minions
    agent_type = args.agent_type
    agent_executable = args.agent_executable
    agent_args = list(args.agent_arg or [])
    chat_now = bool(args.chat)

    if max_minions is not None and max_minions < 0:
        parser.error("--max-minions must be >= 0")

    if interactive:
        from .interactive import ask, choose, confirm, show

        managed = _choose_project_root(root, project_root)
        project_root = _project_ref(root, managed)
        project_id = ask("Dreadnought setup", "Project ID", project_id or managed.name) or managed.name
        directive = ask("Dreadnought setup", "Bootstrap directive / human intent", directive) or directive
        if not directive:
            show("Dreadnought setup", "A bootstrap directive is required.")
            return 2
        objective = ask("Dreadnought setup", "Primary objective", objective or directive) or directive
        existing = project_policy(load_config(root), project_id).max_minions
        default_limit = "" if max_minions is None and existing is None else str(max_minions if max_minions is not None else existing)
        try:
            max_minions = _parse_max_minions(ask("Dreadnought setup", "Maximum concurrent minions (blank = unlimited)", default_limit))
        except ValueError as exc:
            show("Dreadnought setup", str(exc))
            return 2
        if agent_type is None:
            agent_type = choose(
                "Dreadnought setup",
                "Primary Dreadnought agent",
                [("codex", "Codex"), ("cursor", "Cursor"), ("custom", "Custom command"), ("none", "Configure later")],
            )
        if agent_type and agent_type != "none":
            defaults = {"codex": "codex", "cursor": "agent", "custom": ""}
            agent_executable = ask("Dreadnought setup", "Agent executable", agent_executable or defaults.get(agent_type, agent_type))
            arg_text = ask("Dreadnought setup", "Chat arguments (optional)", " ".join(agent_args)) or ""
            agent_args = shlex.split(arg_text)
            chat_now = bool(confirm("Dreadnought setup", "Open the primary agent chat after bootstrap?"))
    elif not directive:
        directive = f"Establish Dreadnought control for {project_id or root.name}."
        objective = objective or directive

    try:
        result = bootstrap_workspace(
            root,
            directive=directive,
            objective=objective or directive,
            requirements=list(args.requirement or []),
            actor=args.actor,
            project_id=project_id,
            project_root=project_root,
            agent_type=agent_type,
            agent_executable=agent_executable,
            agent_args=agent_args,
        )
        policy = set_project_policy(root, str(result["project_id"]), max_minions=max_minions)
        mission_path = Path(result["mission_path"])
        mission = _with_max_minions(Mission.read(mission_path), max_minions)
        mission.write(mission_path)
        instructions_path = Path(result["instructions"])
        instructions_path.write_text(
            _kernel_instructions(
                render_instructions(root, Path(result["project_root"]), mission, dict(result["brain"])),
                max_minions,
            ),
            encoding="utf-8",
        )
        kernel = PrimaryKernel(root).doctor()
        if result.get("primary_agent") and not kernel["available"]:
            raise RuntimeError("Bubblewrap is required before a primary agent can be configured or launched")
        result["policy"] = policy.to_dict()
        result["kernel"] = kernel
    except (OSError, ValueError, RuntimeError, json.JSONDecodeError) as exc:
        if interactive:
            from .interactive import show
            show("Dreadnought setup failed", str(exc))
        else:
            print(f"dreadnought bootstrap failed: {exc}", file=sys.stderr)
        return 2

    if interactive:
        from .interactive import show
        show("Dreadnought ready", json.dumps(result, indent=2))
    else:
        print(json.dumps(result, indent=2))
    if chat_now and result.get("primary_agent"):
        return _launch_primary_agent(root)
    return 0


def run_home_menu(root: Path | None = None) -> int:
    from .interactive import ask, choose, show
    from .mission_builder import mission_menu

    root = (root or Path.cwd()).resolve()
    while True:
        action = choose(
            "Dreadnought",
            f"Workspace: {root}",
            [
                ("init", "Initialize / adopt workspace"),
                ("missions", "Missions"),
                ("chat", "Chat with primary Dreadnought agent"),
                ("query", "Query Grapher brain"),
                ("usage", "Token usage statistics"),
                ("config", "Show project configuration"),
                ("exit", "Exit"),
            ],
        )
        if action in {None, "exit"}:
            return 0
        if action == "init":
            run_bootstrap_cli(["--root", str(root)])
        elif action == "missions":
            mission_menu(root)
        elif action == "chat":
            rc = _launch_primary_agent(root)
            if rc:
                show("Agent chat", "Primary agent is not configured or could not launch.")
        elif action == "query":
            text = ask("Grapher", "Search query", "")
            if text:
                try:
                    hits = GrapherControlPlane(root).query(text, limit=10)
                    show("Grapher results", json.dumps(hits, indent=2)[:12000])
                except (OSError, ValueError) as exc:
                    show("Grapher query", str(exc))
        elif action == "usage":
            show("Token usage", json.dumps(TokenUsageLedger(root).stats(), indent=2))
        elif action == "config":
            show("Configuration", json.dumps(load_config(root), indent=2, sort_keys=True))
