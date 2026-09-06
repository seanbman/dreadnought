from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

from .mission import Mission


def _mission_dir(root: Path) -> Path:
    return root / ".dreadnought" / "missions"


def cmd_mission_init(args: argparse.Namespace) -> int:
    root = Path(args.root).resolve()
    mission = Mission.draft(
        directive=args.directive,
        workspace=str(root),
        actor_id=args.actor,
    )
    errors = mission.validate()
    if errors:
        for error in errors:
            print(f"error: {error}", file=sys.stderr)
        return 2

    path = _mission_dir(root) / f"{mission.id}.json"
    mission.write(path)
    print(path)
    return 0


def cmd_mission_validate(args: argparse.Namespace) -> int:
    path = Path(args.path)
    try:
        mission = Mission.read(path)
    except (OSError, ValueError, TypeError, KeyError, json.JSONDecodeError) as exc:
        print(f"invalid mission document: {exc}", file=sys.stderr)
        return 2

    errors = mission.validate()
    if errors:
        for error in errors:
            print(f"error: {error}", file=sys.stderr)
        return 1
    print("valid")
    return 0


def cmd_mission_show(args: argparse.Namespace) -> int:
    path = Path(args.path)
    mission = Mission.read(path)
    print(json.dumps(mission.to_dict(), indent=2))
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="dreadnought",
        description="Dreadnought agent control plane",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    mission = sub.add_parser("mission", help="create and inspect normalized mission records")
    mission_sub = mission.add_subparsers(dest="mission_command", required=True)

    init = mission_sub.add_parser("init", help="create a mission draft from a human directive")
    init.add_argument("directive", help="natural-language user directive")
    init.add_argument("--root", default=".", help="workspace root")
    init.add_argument("--actor", default="human:user", help="originating actor id")
    init.set_defaults(func=cmd_mission_init)

    validate = mission_sub.add_parser("validate", help="validate a mission document")
    validate.add_argument("path")
    validate.set_defaults(func=cmd_mission_validate)

    show = mission_sub.add_parser("show", help="print a mission document")
    show.add_argument("path")
    show.set_defaults(func=cmd_mission_show)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
