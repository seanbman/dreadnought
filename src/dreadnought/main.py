from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

from dreadnought import __version__
from dreadnought.bootstrap import run_bootstrap_cli, run_home_menu
from dreadnought.mission import Mission
from dreadnought.mission_builder import (
    create_mission_interactive,
    edit_mission_interactive,
    list_missions,
    mark_ready,
    mission_path,
    save_mission,
)
from dreadnought.update import install_release, maybe_notify


def _mission_extension(argv: list[str]) -> int | None:
    if len(argv) < 2 or argv[0] != "mission" or argv[1] not in {"build", "edit", "list", "review", "ready"}:
        return None

    command = argv[1]
    parser = argparse.ArgumentParser(prog=f"dreadnought mission {command}")
    if command not in {"build", "list"}:
        parser.add_argument("mission")
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


def _bootstrap_extension(argv: list[str]) -> int | None:
    if not argv or argv[0] not in {"init", "initialize"}:
        return None
    return run_bootstrap_cli(argv[1:], prog=f"dreadnought {argv[0]}")


def _project_extension(argv: list[str]) -> int | None:
    if not argv or argv[0] != "project":
        return None
    from dreadnought.project_cli import run_project_cli

    return run_project_cli(argv[1:])


def _minion_extension(argv: list[str]) -> int | None:
    if not argv or argv[0] != "minion":
        return None
    from dreadnought.minion import run_minion_cli

    return run_minion_cli(argv[1:])


def _update_command(argv: list[str]) -> int | None:
    if not argv or argv[0] != "update":
        return None
    parser = argparse.ArgumentParser(prog="dreadnought update")
    parser.add_argument("--version", dest="tag")
    args = parser.parse_args(argv[1:])
    try:
        tag = install_release(args.tag)
    except (RuntimeError, ValueError) as exc:
        print(f"update failed: {exc}", file=sys.stderr)
        return 2
    print(f"Updated Dreadnought to {tag}. Restart the command to use the new version.")
    return 0


def _print_help() -> int:
    print(
        "Dreadnought agent control plane\n\n"
        "Usage:\n"
        "  dreadnought                          open the interactive workspace menu\n"
        "  dreadnought initialize [brief]       initialize/adopt a workspace and generate instructions\n"
        "  dreadnought init [brief]             alias for initialize\n"
        "  dreadnought project <command>        register/list/select workspace projects\n"
        "  dreadnought mission <command>        build or inspect missions\n"
        "  dreadnought doctrine <command>       normalize authoritative intent\n"
        "  dreadnought campaign <command>       plan doctrine as bounded operations\n"
        "  dreadnought order <command>          issue a Project Arm order\n"
        "  dreadnought minion commission ...    commission a configured subordinate agent\n"
        "  dreadnought grapher <command>        broker managed Grapher access\n"
        "  dreadnought protocol <command>       validate or ingest typed testimony\n"
        "  dreadnought arm dispatch ...         execute a bounded Project Arm order\n"
        "  dreadnought agent <command>          configure/open an agent adapter\n"
        "  dreadnought usage <command>          record or summarize token usage\n"
        "  dreadnought config <command>         inspect/change project configuration\n"
        "  dreadnought update                   update the managed installation\n"
        "  dreadnought --version                print the installed version\n\n"
        "Run `dreadnought <command> --help` for command-specific options.\n\n"
        "Interactive controls:\n"
        "  ↑/↓ or 1..N  select menu items\n"
        "  q            back / exit a menu\n"
        "  Esc, Ctrl-C  cancel the current prompt and exit cleanly\n\n"
        "Manual:\n"
        "  man dreadnought"
    )
    return 0


def main() -> int:
    actual = list(sys.argv[1:])
    interactive = sys.stdin.isatty() and sys.stdout.isatty()
    if interactive:
        maybe_notify(__version__)

    if actual == ["--version"]:
        print(__version__)
        return 0
    if actual in (["help"], ["--help"], ["-h"]):
        return _print_help()
    if not actual and interactive:
        return run_home_menu()

    bootstrapped = _bootstrap_extension(actual)
    if bootstrapped is not None:
        return bootstrapped
    projects = _project_extension(actual)
    if projects is not None:
        return projects
    minion = _minion_extension(actual)
    if minion is not None:
        return minion
    updated = _update_command(actual)
    if updated is not None:
        return updated
    extended = _mission_extension(actual)
    if extended is not None:
        return extended

    from dreadnought.cli import main as cli_main
    return cli_main(actual)


if __name__ == "__main__":
    raise SystemExit(main())
