from __future__ import annotations

import argparse
import json
from pathlib import Path

from .multi_project import MultiProjectControlPlane
from .project_factory import create_project
from .project_registry import list_projects, register_project, select_project, unregister_project
from .protocol import ProtocolRecord


def run_project_cli(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(prog="dreadnought project", description="Manage projects in a Dreadnought workspace")
    parser.add_argument("--root", default=".", help=argparse.SUPPRESS)
    sub = parser.add_subparsers(dest="project_command", required=True)

    listing = sub.add_parser("list", help="list registered projects")
    listing.add_argument("--root", default=".")

    status = sub.add_parser("status", help="check one or more project brains without switching the default")
    status.add_argument("project_id", nargs="*")
    status.add_argument("--root", default=".")

    query = sub.add_parser("query", help="query multiple project brains synchronously")
    query.add_argument("text")
    query.add_argument("--project", action="append", default=[])
    query.add_argument("--limit", type=int, default=10)
    query.add_argument("--mission")
    query.add_argument("--root", default=".")

    ingest = sub.add_parser("ingest", help="ingest a typed protocol record into one project's brain")
    ingest.add_argument("project_id")
    ingest.add_argument("path")
    ingest.add_argument("--root", default=".")

    create = sub.add_parser("create", help="create and register a complete Dreadnought-managed project")
    create.add_argument("name")
    create.add_argument("directive")
    create.add_argument("--id")
    create.add_argument("--docs-source", help="existing documentation directory to link as project/docs")
    create.add_argument("--actor", default="human:user")
    create.add_argument("--default", action="store_true", dest="make_default")
    create.add_argument("--root", default=".")

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
        if args.project_command == "status":
            result = MultiProjectControlPlane(workspace).status(args.project_id or None)
            print(json.dumps(result, indent=2, sort_keys=True))
            return 0 if all(item["ready"] for item in result.values()) else 1
        if args.project_command == "query":
            result = MultiProjectControlPlane(workspace).query(
                args.text,
                project_ids=args.project or None,
                limit=args.limit,
                mission=args.mission,
            )
            print(json.dumps(result, indent=2, sort_keys=True))
            return 0
        if args.project_command == "ingest":
            record = ProtocolRecord.read(Path(args.path))
            result = MultiProjectControlPlane(workspace).write_record(args.project_id, record)
            print(json.dumps({"project_id": args.project_id, "record_id": result.record_id}, indent=2))
            return 0
        if args.project_command == "create":
            result = create_project(
                workspace,
                args.name,
                args.directive,
                project_id=args.id,
                docs_source=args.docs_source,
                actor=args.actor,
                make_default=True if args.make_default else None,
            )
            print(json.dumps(result, indent=2))
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
    except (OSError, ValueError, RuntimeError, TypeError, KeyError, json.JSONDecodeError) as exc:
        parser.error(str(exc))
    return 2
