from __future__ import annotations

import argparse
import json
from pathlib import Path
import shlex
import subprocess
import sys

from .agent import CommandAgentAdapter
from .campaign import CampaignPlan
from .config import configure_agent, default_config, load_config, save_config
from .dispatch import ProjectArmDispatcher
from .doctrine import Doctrine
from .grapher import GrapherControlPlane
from .mission import Mission
from .order import Order
from .protocol import ProtocolRecord
from .usage import TokenUsage, TokenUsageLedger


def _dn_dir(root: Path, kind: str) -> Path:
    return root / ".dreadnought" / kind


def _validate_document(path: Path, cls, label: str) -> int:
    try:
        document = cls.read(path)
    except (OSError, ValueError, TypeError, KeyError, json.JSONDecodeError) as exc:
        print(f"invalid {label} document: {exc}", file=sys.stderr)
        return 2
    errors = document.validate()
    if errors:
        for error in errors:
            print(f"error: {error}", file=sys.stderr)
        return 1
    print("valid")
    return 0


def _show_document(path: Path, cls) -> int:
    document = cls.read(path)
    print(json.dumps(document.to_dict(), indent=2))
    return 0


def cmd_init(args: argparse.Namespace) -> int:
    root = Path(args.root).resolve()
    root.mkdir(parents=True, exist_ok=True)
    interactive = not args.non_interactive
    project_id = args.project_id
    agent_type = args.agent_type
    executable = args.agent_executable
    agent_args = list(args.agent_arg or [])
    chat_now = bool(args.chat)

    if interactive:
        from .interactive import ask, choose, confirm, show
        project_id = ask("Dreadnought setup", "Project ID", project_id or root.name) or root.name
        if agent_type is None:
            agent_type = choose(
                "Dreadnought setup",
                "Primary Dreadnought agent",
                [("codex", "Codex"), ("cursor", "Cursor"), ("custom", "Custom command"), ("none", "Configure later")],
            )
        if agent_type and agent_type != "none":
            defaults = {"codex": "codex", "cursor": "agent", "custom": ""}
            executable = ask("Dreadnought setup", "Agent executable", executable or defaults.get(agent_type, agent_type))
            arg_text = ask("Dreadnought setup", "Chat arguments (optional)", " ".join(agent_args)) or ""
            agent_args = shlex.split(arg_text)
            chat_now = confirm("Dreadnought setup", "Open the primary agent chat after setup?")

    cfg = load_config(root) if (root / ".dreadnought" / "config.json").exists() else default_config(root)
    cfg["project_id"] = project_id or root.name
    save_config(root, cfg)

    plane = GrapherControlPlane(root)
    if not plane.graph_path.exists():
        plane.initialize()

    if agent_type and agent_type != "none":
        configure_agent(root, agent_type=agent_type, executable=executable, args=agent_args, primary=True)

    result = {"root": str(root), "project_id": load_config(root)["project_id"], "grapher": plane.doctor(), "primary_agent": load_config(root).get("primary_agent")}
    if interactive:
        show("Dreadnought ready", json.dumps(result, indent=2))
    else:
        print(json.dumps(result, indent=2))
    if chat_now and load_config(root).get("primary_agent"):
        return _launch_agent_chat(root, load_config(root)["primary_agent"])
    return 0


def cmd_agent_init(args: argparse.Namespace) -> int:
    root = Path(args.root).resolve()
    config = configure_agent(
        root,
        agent_type=args.agent_type,
        executable=args.executable,
        args=list(args.agent_arg or []),
        primary=args.primary,
    )
    print(json.dumps(config["agents"][args.agent_type], indent=2))
    if args.chat:
        return _launch_agent_chat(root, args.agent_type)
    return 0


def _launch_agent_chat(root: Path, agent_type: str) -> int:
    config = load_config(root)
    agent = (config.get("agents") or {}).get(agent_type)
    if not agent:
        print(f"agent is not configured: {agent_type}", file=sys.stderr)
        return 2
    command = [agent["executable"], *list(agent.get("args") or [])]
    print(f"Opening {agent_type} chat in {root} ...", file=sys.stderr)
    try:
        rc = subprocess.call(command, cwd=root)
    except FileNotFoundError:
        print(f"agent executable not found: {agent['executable']}", file=sys.stderr)
        return 2
    if bool((config.get("token_usage") or {}).get("enabled", True)):
        TokenUsageLedger(root).record_unmetered_session(
            agent_id=str(agent_type),
            agent_role="primary",
            project_id=str(config.get("active_project") or config.get("project_id") or root.name),
            exit_code=rc,
        )
    return rc


def cmd_agent_chat(args: argparse.Namespace) -> int:
    root = Path(args.root).resolve()
    config = load_config(root)
    agent_type = args.agent_type or config.get("primary_agent")
    if not agent_type:
        print("no primary agent configured; run `dreadnought agent init ... --primary`", file=sys.stderr)
        return 2
    return _launch_agent_chat(root, agent_type)


def cmd_config_show(args: argparse.Namespace) -> int:
    print(json.dumps(load_config(Path(args.root).resolve()), indent=2, sort_keys=True))
    return 0


def cmd_config_set(args: argparse.Namespace) -> int:
    root = Path(args.root).resolve()
    config = load_config(root)
    if args.project_id is not None:
        config["project_id"] = args.project_id
    if args.primary_agent is not None:
        if args.primary_agent not in (config.get("agents") or {}):
            print(f"agent is not configured: {args.primary_agent}", file=sys.stderr)
            return 2
        config["primary_agent"] = args.primary_agent
    save_config(root, config)
    print(json.dumps(config, indent=2, sort_keys=True))
    return 0


def cmd_usage_record(args: argparse.Namespace) -> int:
    root = Path(args.root).resolve()
    config = load_config(root)
    usage = TokenUsage.create(
        agent_id=args.agent,
        agent_role=args.role,
        project_id=args.project or config.get("project_id") or root.name,
        task_id=args.task,
        input_tokens=args.input_tokens,
        output_tokens=args.output_tokens,
        cached_tokens=args.cached_tokens,
        reasoning_tokens=args.reasoning_tokens,
        provider=args.provider,
        model=args.model,
        source=args.source,
    )
    try:
        TokenUsageLedger(root).record(usage, project_to_grapher=not args.no_grapher)
    except (OSError, ValueError) as exc:
        print(f"usage record failed: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(usage.to_dict(), indent=2, sort_keys=True))
    return 0


def cmd_usage_stats(args: argparse.Namespace) -> int:
    stats = TokenUsageLedger(Path(args.root).resolve()).stats(project_id=args.project, task_id=args.task, agent_role=args.role)
    print(json.dumps(stats, indent=2, sort_keys=True))
    return 0


def cmd_mission_init(args: argparse.Namespace) -> int:
    root = Path(args.root).resolve()
    mission = Mission.draft(directive=args.directive, workspace=str(root), actor_id=args.actor)
    errors = mission.validate()
    if errors:
        for error in errors:
            print(f"error: {error}", file=sys.stderr)
        return 2
    path = _dn_dir(root, "missions") / f"{mission.id}.json"
    mission.write(path)
    print(path)
    return 0


def cmd_doctrine_init(args: argparse.Namespace) -> int:
    root = Path(args.root).resolve()
    doctrine = Doctrine.draft(objective=args.objective, actor_id=args.actor)
    path = _dn_dir(root, "doctrine") / f"{doctrine.id}.json"
    doctrine.write(path)
    print(path)
    return 0


def cmd_campaign_init(args: argparse.Namespace) -> int:
    root = Path(args.root).resolve()
    campaign = CampaignPlan.draft(doctrine_ref=args.doctrine, task_group=args.task_group)
    path = _dn_dir(root, "campaigns") / f"{campaign.id}.json"
    campaign.write(path)
    print(path)
    return 0


def cmd_order_init(args: argparse.Namespace) -> int:
    root = Path(args.root).resolve()
    order = Order.draft(doctrine_ref=args.doctrine, campaign_ref=args.campaign, operation_ref=args.operation, objective=args.objective, project_arm=args.project_arm)
    path = _dn_dir(root, "orders") / f"{order.id}.json"
    order.write(path)
    print(path)
    return 0


def cmd_protocol_ingest(args: argparse.Namespace) -> int:
    root = Path(args.root).resolve()
    try:
        record = ProtocolRecord.read(Path(args.path))
        result = GrapherControlPlane(root).write_record(record)
    except (OSError, ValueError, TypeError, KeyError, json.JSONDecodeError) as exc:
        print(f"protocol ingest failed: {exc}", file=sys.stderr)
        return 2
    print(result.record_id)
    return 0


def cmd_grapher_init(args: argparse.Namespace) -> int:
    root = Path(args.root).resolve()
    try:
        path = GrapherControlPlane(root).initialize()
    except (OSError, ValueError) as exc:
        print(f"grapher init failed: {exc}", file=sys.stderr)
        return 2
    print(path)
    return 0


def cmd_grapher_doctor(args: argparse.Namespace) -> int:
    result = GrapherControlPlane(Path(args.root).resolve()).doctor()
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result.get("compatible") else 1


def cmd_grapher_query(args: argparse.Namespace) -> int:
    try:
        hits = GrapherControlPlane(Path(args.root).resolve()).query(args.text, limit=args.limit, mission=args.mission)
    except (OSError, ValueError) as exc:
        print(f"grapher query failed: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(hits, indent=2, sort_keys=True))
    return 0


def cmd_grapher_get(args: argparse.Namespace) -> int:
    try:
        detail = GrapherControlPlane(Path(args.root).resolve()).get(args.node_id)
    except (OSError, ValueError) as exc:
        print(f"grapher get failed: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(detail, indent=2, sort_keys=True))
    return 0


def cmd_arm_dispatch(args: argparse.Namespace) -> int:
    root = Path(args.root).resolve()
    scratch = Path(args.scratch).resolve()
    try:
        order = Order.read(Path(args.order))
        adapter = CommandAgentAdapter(id=args.adapter, executable=args.executable, args=tuple(args.agent_arg or []))
        result = ProjectArmDispatcher(workspace=root, scratch=scratch).dispatch(order, adapter, timeout=args.timeout)
    except (OSError, ValueError, TypeError, KeyError, json.JSONDecodeError, RuntimeError) as exc:
        print(f"arm dispatch failed: {exc}", file=sys.stderr)
        return 2
    print(json.dumps({"order_id": result.order_id, "project_arm": result.project_arm, "adapter_id": result.adapter_id, "exit_code": result.exit_code, "observation_id": result.observation_id}, indent=2))
    return 0 if result.exit_code == 0 else 1


def _wire_document_commands(parent, label: str, cls) -> None:
    validate = parent.add_parser("validate", help=f"validate a {label} document")
    validate.add_argument("path")
    validate.set_defaults(func=lambda args: _validate_document(Path(args.path), cls, label))
    show = parent.add_parser("show", help=f"print a {label} document")
    show.add_argument("path")
    show.set_defaults(func=lambda args: _show_document(Path(args.path), cls))


def run_menu(root: Path | None = None) -> int:
    from .interactive import ask, choose, show
    root = (root or Path.cwd()).resolve()
    while True:
        action = choose(
            "Dreadnought",
            f"Project: {root}",
            [
                ("init", "Initialize / reconfigure project"),
                ("chat", "Chat with primary Dreadnought agent"),
                ("agent", "Configure an agent"),
                ("query", "Query Grapher brain"),
                ("usage", "Token usage statistics"),
                ("config", "Edit project configuration"),
                ("exit", "Exit"),
            ],
        )
        if action in {None, "exit"}:
            return 0
        if action == "init":
            return main(["init", "--root", str(root)])
        if action == "chat":
            rc = cmd_agent_chat(argparse.Namespace(root=str(root), agent_type=None))
            if rc:
                show("Agent chat", "Primary agent is not configured or could not launch.")
        elif action == "agent":
            agent_type = choose("Configure agent", "Agent type", [("codex", "Codex"), ("cursor", "Cursor"), ("custom", "Custom")])
            if agent_type:
                defaults = {"codex": "codex", "cursor": "agent", "custom": ""}
                executable = ask("Configure agent", "Executable", defaults.get(agent_type, "")) or agent_type
                arg_text = ask("Configure agent", "Chat arguments", "") or ""
                configure_agent(root, agent_type=agent_type, executable=executable, args=shlex.split(arg_text), primary=True)
        elif action == "query":
            text = ask("Grapher", "Search query", "")
            if text:
                hits = GrapherControlPlane(root).query(text, limit=10)
                show("Grapher results", json.dumps(hits, indent=2)[:12000])
        elif action == "usage":
            show("Token usage", json.dumps(TokenUsageLedger(root).stats(), indent=2))
        elif action == "config":
            config = load_config(root)
            project_id = ask("Configuration", "Project ID", config.get("project_id") or root.name)
            if project_id:
                config["project_id"] = project_id
                save_config(root, config)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="dreadnought", description="Dreadnought agent control plane")
    sub = parser.add_subparsers(dest="command")

    setup = sub.add_parser("init", help="guided project, Grapher, and primary-agent setup")
    setup.add_argument("--root", default=".")
    setup.add_argument("--project-id")
    setup.add_argument("--agent-type")
    setup.add_argument("--agent-executable")
    setup.add_argument("--agent-arg", action="append", default=[])
    setup.add_argument("--chat", action="store_true")
    setup.add_argument("--non-interactive", action="store_true")
    setup.set_defaults(func=cmd_init)

    agent = sub.add_parser("agent", help="configure and chat with primary/minion agents")
    agent_sub = agent.add_subparsers(dest="agent_command", required=True)
    ainit = agent_sub.add_parser("init", help="configure an agent type directly")
    ainit.add_argument("agent_type")
    ainit.add_argument("--root", default=".")
    ainit.add_argument("--executable")
    ainit.add_argument("--agent-arg", action="append", default=[])
    ainit.add_argument("--primary", action="store_true")
    ainit.add_argument("--chat", action="store_true")
    ainit.set_defaults(func=cmd_agent_init)
    chat = agent_sub.add_parser("chat", help="open the configured agent's native interactive chat")
    chat.add_argument("agent_type", nargs="?")
    chat.add_argument("--root", default=".")
    chat.set_defaults(func=cmd_agent_chat)

    config_cmd = sub.add_parser("config", help="show or change Dreadnought project config")
    config_sub = config_cmd.add_subparsers(dest="config_command", required=True)
    cshow = config_sub.add_parser("show")
    cshow.add_argument("--root", default=".")
    cshow.set_defaults(func=cmd_config_show)
    cset = config_sub.add_parser("set")
    cset.add_argument("--root", default=".")
    cset.add_argument("--project-id")
    cset.add_argument("--primary-agent")
    cset.set_defaults(func=cmd_config_set)

    usage = sub.add_parser("usage", help="record and summarize agent token usage")
    usage_sub = usage.add_subparsers(dest="usage_command", required=True)
    urecord = usage_sub.add_parser("record", help="record provider-reported usage and project it into Grapher")
    urecord.add_argument("--root", default=".")
    urecord.add_argument("--agent", required=True)
    urecord.add_argument("--role", choices=["primary", "minion"], required=True)
    urecord.add_argument("--project")
    urecord.add_argument("--task")
    urecord.add_argument("--input-tokens", type=int, required=True)
    urecord.add_argument("--output-tokens", type=int, required=True)
    urecord.add_argument("--cached-tokens", type=int, default=0)
    urecord.add_argument("--reasoning-tokens", type=int, default=0)
    urecord.add_argument("--provider")
    urecord.add_argument("--model")
    urecord.add_argument("--source", default="reported")
    urecord.add_argument("--no-grapher", action="store_true")
    urecord.set_defaults(func=cmd_usage_record)
    ustats = usage_sub.add_parser("stats", help="aggregate token usage collectively or by project/task/role")
    ustats.add_argument("--root", default=".")
    ustats.add_argument("--project")
    ustats.add_argument("--task")
    ustats.add_argument("--role", choices=["primary", "minion"])
    ustats.set_defaults(func=cmd_usage_stats)

    mission = sub.add_parser("mission", help="create and inspect normalized mission records")
    mission_sub = mission.add_subparsers(dest="mission_command", required=True)
    init = mission_sub.add_parser("init", help="create a mission draft from a human directive")
    init.add_argument("directive"); init.add_argument("--root", default="."); init.add_argument("--actor", default="human:user"); init.set_defaults(func=cmd_mission_init)
    _wire_document_commands(mission_sub, "mission", Mission)

    doctrine = sub.add_parser("doctrine", help="normalize authoritative project intent")
    doctrine_sub = doctrine.add_subparsers(dest="doctrine_command", required=True)
    dinit = doctrine_sub.add_parser("init"); dinit.add_argument("objective"); dinit.add_argument("--root", default="."); dinit.add_argument("--actor", default="human:user"); dinit.set_defaults(func=cmd_doctrine_init)
    _wire_document_commands(doctrine_sub, "doctrine", Doctrine)

    campaign = sub.add_parser("campaign", help="plan doctrine as PR-sized operations")
    campaign_sub = campaign.add_subparsers(dest="campaign_command", required=True)
    cinit = campaign_sub.add_parser("init"); cinit.add_argument("--doctrine", required=True); cinit.add_argument("--task-group", default="task-group-1"); cinit.add_argument("--root", default="."); cinit.set_defaults(func=cmd_campaign_init)
    _wire_document_commands(campaign_sub, "campaign", CampaignPlan)

    order = sub.add_parser("order", help="issue a compartmentalized order to a project arm")
    order_sub = order.add_subparsers(dest="order_command", required=True)
    oinit = order_sub.add_parser("init"); oinit.add_argument("objective"); oinit.add_argument("--doctrine", required=True); oinit.add_argument("--campaign", required=True); oinit.add_argument("--operation", required=True); oinit.add_argument("--project-arm", default="project-arm-1"); oinit.add_argument("--root", default="."); oinit.set_defaults(func=cmd_order_init)
    _wire_document_commands(order_sub, "order", Order)

    protocol = sub.add_parser("protocol", help="validate and ingest typed protocol records")
    protocol_sub = protocol.add_subparsers(dest="protocol_command", required=True)
    _wire_document_commands(protocol_sub, "protocol", ProtocolRecord)
    ingest = protocol_sub.add_parser("ingest"); ingest.add_argument("path"); ingest.add_argument("--root", default="."); ingest.set_defaults(func=cmd_protocol_ingest)

    grapher_cmd = sub.add_parser("grapher", help="initialize and broker access to Dreadnought's embedded Grapher brain")
    grapher_sub = grapher_cmd.add_subparsers(dest="grapher_command", required=True)
    ginit = grapher_sub.add_parser("init"); ginit.add_argument("--root", default="."); ginit.set_defaults(func=cmd_grapher_init)
    doctor = grapher_sub.add_parser("doctor"); doctor.add_argument("--root", default="."); doctor.set_defaults(func=cmd_grapher_doctor)
    query = grapher_sub.add_parser("query"); query.add_argument("text"); query.add_argument("--root", default="."); query.add_argument("--limit", type=int, default=10); query.add_argument("--mission"); query.set_defaults(func=cmd_grapher_query)
    get = grapher_sub.add_parser("get"); get.add_argument("node_id"); get.add_argument("--root", default="."); get.set_defaults(func=cmd_grapher_get)

    arm = sub.add_parser("arm", help="dispatch compartmentalized Orders to Project Arms")
    arm_sub = arm.add_subparsers(dest="arm_command", required=True)
    dispatch = arm_sub.add_parser("dispatch"); dispatch.add_argument("order"); dispatch.add_argument("--root", default="."); dispatch.add_argument("--scratch", required=True); dispatch.add_argument("--adapter", required=True); dispatch.add_argument("--executable", required=True); dispatch.add_argument("--agent-arg", action="append", default=[]); dispatch.add_argument("--timeout", type=int, default=300); dispatch.set_defaults(func=cmd_arm_dispatch)
    return parser


def main(argv: list[str] | None = None) -> int:
    actual = list(sys.argv[1:] if argv is None else argv)
    if not actual:
        return run_menu()
    parser = build_parser()
    args = parser.parse_args(actual)
    if not hasattr(args, "func"):
        parser.print_help()
        return 2
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
