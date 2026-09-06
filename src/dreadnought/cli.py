from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

from .campaign import CampaignPlan
from .doctrine import Doctrine
from .mission import Mission
from .order import Order


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

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
