from __future__ import annotations

import argparse
import json
from pathlib import Path

from .project_registry import list_projects, register_project, select_project, unregister_project


def run_project_cli(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(prog="dreadnought project", description="Manage projects in a Dreadnought workspace")
    parser.add_argument("--root", default=".", help=argparse.SUPPRESS)
    sub = parser.add_subparsers(dest="project_command", required=True)

    listing = sub.add_parser("list", help="list registered projects")
    listing.add_argument("--root", default=".")

    add = sub.add_parser("add", help="register an existing project directory")
    add.add_argument("path")
    add.add_argument("--id")
    add.add_argument("--directive")
    add.add_argument("--docs-root")
    add.add_argument("--default", action="store_true", dest="make_default")
    add.add_argument("--root", default=".")

    select = sub.add_parser("select", help="set the default project for unscoped commands")
    select.add_argument("project_id")
    select.add_argument("--root", default=".")

    remove = sub.add_parser("remove", help="unregister a project without deleting its files")
    remove.add_argument("project_id")
    remove.add_argument("--root", default=".")

    args = parser.parse_args(argv)
    workspace = Path(args.root).resolve()

    try:
        if args.project_command == "list":
            print(json.dumps(list_projects(workspace), indent=2))
            return 0
        if args.project_command == "add":
            record = register_project(
                workspace,
                args.path,
                project_id=args.id,
                directive=args.directive,
                docs_root=args.docs_root,
                make_default=True if args.make_default else None,
            )
            print(json.dumps(record.to_dict(), indent=2))
            return 0
        if args.project_command == "select":
            record = select_project(workspace, args.project_id)
            print(json.dumps(record.to_dict(), indent=2))
            return 0
        if args.project_command == "remove":
            record = unregister_project(workspace, args.project_id)
            print(json.dumps(record.to_dict(), indent=2))
            return 0
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        parser.error(str(exc))
    return 2
