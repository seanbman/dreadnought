from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

from .agent import CommandAgentAdapter
from .campaign import CampaignPlan
from .dispatch import ProjectArmDispatcher
from .doctrine import Doctrine
from .grapher import GrapherControlPlane
from .mission import Mission
from .order import Order
from .protocol import ProtocolRecord


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
    order = Order.draft(
        doctrine_ref=args.doctrine,
        campaign_ref=args.campaign,
        operation_ref=args.operation,
        objective=args.objective,
        project_arm=args.project_arm,
    )
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
    root = Path(args.root).resolve()
    result = GrapherControlPlane(root).doctor()
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result.get("compatible") else 1


def cmd_grapher_query(args: argparse.Namespace) -> int:
    root = Path(args.root).resolve()
    try:
        hits = GrapherControlPlane(root).query(args.text, limit=args.limit, mission=args.mission)
    except (OSError, ValueError) as exc:
        print(f"grapher query failed: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(hits, indent=2, sort_keys=True))
    return 0


def cmd_grapher_get(args: argparse.Namespace) -> int:
    root = Path(args.root).resolve()
    try:
        detail = GrapherControlPlane(root).get(args.node_id)
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
        adapter = CommandAgentAdapter(
            id=args.adapter,
            executable=args.executable,
            args=tuple(args.agent_arg or []),
        )
        result = ProjectArmDispatcher(workspace=root, scratch=scratch).dispatch(
            order,
            adapter,
            timeout=args.timeout,
        )
    except (OSError, ValueError, TypeError, KeyError, json.JSONDecodeError, RuntimeError) as exc:
        print(f"arm dispatch failed: {exc}", file=sys.stderr)
        return 2
    print(json.dumps({
        "order_id": result.order_id,
        "project_arm": result.project_arm,
        "adapter_id": result.adapter_id,
        "exit_code": result.exit_code,
        "observation_id": result.observation_id,
    }, indent=2))
    return 0 if result.exit_code == 0 else 1


def _wire_document_commands(parent, label: str, cls) -> None:
    validate = parent.add_parser("validate", help=f"validate a {label} document")
    validate.add_argument("path")
    validate.set_defaults(func=lambda args: _validate_document(Path(args.path), cls, label))

    show = parent.add_parser("show", help=f"print a {label} document")
    show.add_argument("path")
    show.set_defaults(func=lambda args: _show_document(Path(args.path), cls))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="dreadnought", description="Dreadnought agent control plane")
    sub = parser.add_subparsers(dest="command", required=True)

    mission = sub.add_parser("mission", help="create and inspect normalized mission records")
    mission_sub = mission.add_subparsers(dest="mission_command", required=True)
    init = mission_sub.add_parser("init", help="create a mission draft from a human directive")
    init.add_argument("directive")
    init.add_argument("--root", default=".")
    init.add_argument("--actor", default="human:user")
    init.set_defaults(func=cmd_mission_init)
    _wire_document_commands(mission_sub, "mission", Mission)

    doctrine = sub.add_parser("doctrine", help="normalize authoritative project intent")
    doctrine_sub = doctrine.add_subparsers(dest="doctrine_command", required=True)
    dinit = doctrine_sub.add_parser("init", help="create a doctrine draft")
    dinit.add_argument("objective")
    dinit.add_argument("--root", default=".")
    dinit.add_argument("--actor", default="human:user")
    dinit.set_defaults(func=cmd_doctrine_init)
    _wire_document_commands(doctrine_sub, "doctrine", Doctrine)

    campaign = sub.add_parser("campaign", help="plan doctrine as PR-sized operations")
    campaign_sub = campaign.add_subparsers(dest="campaign_command", required=True)
    cinit = campaign_sub.add_parser("init", help="create an empty campaign plan")
    cinit.add_argument("--doctrine", required=True)
    cinit.add_argument("--task-group", default="task-group-1")
    cinit.add_argument("--root", default=".")
    cinit.set_defaults(func=cmd_campaign_init)
    _wire_document_commands(campaign_sub, "campaign", CampaignPlan)

    order = sub.add_parser("order", help="issue a compartmentalized order to a project arm")
    order_sub = order.add_subparsers(dest="order_command", required=True)
    oinit = order_sub.add_parser("init", help="create a project arm order")
    oinit.add_argument("objective")
    oinit.add_argument("--doctrine", required=True)
    oinit.add_argument("--campaign", required=True)
    oinit.add_argument("--operation", required=True)
    oinit.add_argument("--project-arm", default="project-arm-1")
    oinit.add_argument("--root", default=".")
    oinit.set_defaults(func=cmd_order_init)
    _wire_document_commands(order_sub, "order", Order)

    protocol = sub.add_parser("protocol", help="validate and ingest typed protocol records")
    protocol_sub = protocol.add_subparsers(dest="protocol_command", required=True)
    _wire_document_commands(protocol_sub, "protocol", ProtocolRecord)
    ingest = protocol_sub.add_parser("ingest", help="validate and write a protocol record through Dreadnought into Grapher")
    ingest.add_argument("path")
    ingest.add_argument("--root", default=".")
    ingest.set_defaults(func=cmd_protocol_ingest)

    grapher_cmd = sub.add_parser("grapher", help="initialize and broker access to Dreadnought's embedded Grapher brain")
    grapher_sub = grapher_cmd.add_subparsers(dest="grapher_command", required=True)
    ginit = grapher_sub.add_parser("init", help="initialize a Dreadnought-managed Grapher brain and policy config")
    ginit.add_argument("--root", default=".")
    ginit.set_defaults(func=cmd_grapher_init)
    doctor = grapher_sub.add_parser("doctor", help="check Dreadnought/Grapher compatibility and configuration")
    doctor.add_argument("--root", default=".")
    doctor.set_defaults(func=cmd_grapher_doctor)
    query = grapher_sub.add_parser("query", help="search Grapher through the Dreadnought read broker")
    query.add_argument("text")
    query.add_argument("--root", default=".")
    query.add_argument("--limit", type=int, default=10)
    query.add_argument("--mission")
    query.set_defaults(func=cmd_grapher_query)
    get = grapher_sub.add_parser("get", help="read one Grapher node through the Dreadnought broker")
    get.add_argument("node_id")
    get.add_argument("--root", default=".")
    get.set_defaults(func=cmd_grapher_get)

    arm = sub.add_parser("arm", help="dispatch compartmentalized Orders to Project Arms")
    arm_sub = arm.add_subparsers(dest="arm_command", required=True)
    dispatch = arm_sub.add_parser("dispatch", help="execute one Order through Sarcophagus using a command adapter")
    dispatch.add_argument("order")
    dispatch.add_argument("--root", default=".")
    dispatch.add_argument("--scratch", required=True, help="writable scratch directory outside the canonical workspace")
    dispatch.add_argument("--adapter", required=True, help="stable adapter identifier")
    dispatch.add_argument("--executable", required=True, help="external agent executable")
    dispatch.add_argument("--agent-arg", action="append", default=[], help="repeatable adapter argument; supports explicit template tokens")
    dispatch.add_argument("--timeout", type=int, default=300)
    dispatch.set_defaults(func=cmd_arm_dispatch)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
