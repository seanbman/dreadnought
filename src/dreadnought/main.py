from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

from dreadnought import __version__
from dreadnought.mission import Mission
from dreadnought.mission_builder import (
    create_mission_interactive,
    edit_mission_interactive,
    list_missions,
    mark_ready,
    mission_path,
    run_home_menu,
    save_mission,
)
from dreadnought.update import maybe_notify


def _mission_extension(argv: list[str]) -> int | None:
    if len(argv) < 2 or argv[0] != "mission" or argv[1] not in {"build", "edit", "list", "review", "ready"}:
        return None

    command = argv[1]
    parser = argparse.ArgumentParser(prog=f"dreadnought mission {command}")
    parser.add_argument("mission", nargs="?" if command in {"build", "list"} else None)
    parser.add_argument("--root", default=".")
    if command == "build":
        parser.add_argument("--actor", default="human:user")
    args = parser.parse_args(argv[2:])
    root = Path(args.root).resolve()

    if command == "list":
        print(json.dumps(list_missions(root), indent=2))
        return 0
    if command == "build":
        if not (sys.stdin.isatty() and sys.stdout.isatty()):
            print("mission build requires an interactive terminal; use `mission init` for scripted creation", file=sys.stderr)
            return 2
        path = create_mission_interactive(root, actor=args.actor)
        if path is None:
            return 1
        print(path)
        return 0

    path = mission_path(root, args.mission)
    if not path.exists():
        print(f"mission not found: {args.mission}", file=sys.stderr)
        return 2
    mission = Mission.read(path)

    if command == "review":
        print(json.dumps(mission.to_dict(), indent=2))
        return 0
    if command == "edit":
        if not (sys.stdin.isatty() and sys.stdout.isatty()):
            print("mission edit requires an interactive terminal", file=sys.stderr)
            return 2
        edit_mission_interactive(root, mission)
        print(save_mission(root, mission))
        return 0
    if command == "ready":
        try:
            mark_ready(mission)
            print(save_mission(root, mission))
        except ValueError as exc:
            print(f"mission not ready: {exc}", file=sys.stderr)
            return 1
        return 0
    return None


def main() -> int:
    actual = list(sys.argv[1:])
    interactive = sys.stdin.isatty() and sys.stdout.isatty()
    if interactive:
        maybe_notify(__version__)

    if actual == ["--version"]:
        print(__version__)
        return 0
    if not actual and interactive:
        return run_home_menu()

    extended = _mission_extension(actual)
    if extended is not None:
        return extended

    from dreadnought.cli import main as cli_main
    return cli_main(actual)


if __name__ == "__main__":
    raise SystemExit(main())
