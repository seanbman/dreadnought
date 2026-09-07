from __future__ import annotations

import json
from pathlib import Path
import shlex
from typing import Iterable

from .config import configure_agent, load_config, save_config
from .grapher import GrapherControlPlane
from .mission import AccessMode, CapabilitySet, Mission, MissionStatus, Source, SourceType
from .usage import TokenUsageLedger


def missions_dir(root: Path) -> Path:
    return root.resolve() / ".dreadnought" / "missions"


def mission_path(root: Path, mission_ref: str) -> Path:
    candidate = Path(mission_ref)
    if candidate.exists():
        return candidate.resolve()
    name = mission_ref if mission_ref.endswith(".json") else f"{mission_ref}.json"
    return missions_dir(root) / name


def list_missions(root: Path) -> list[dict[str, str]]:
    directory = missions_dir(root)
    if not directory.exists():
        return []
    rows: list[dict[str, str]] = []
    for path in sorted(directory.glob("*.json")):
        try:
            mission = Mission.read(path)
        except (OSError, ValueError, TypeError, KeyError, json.JSONDecodeError):
            rows.append({"id": path.stem, "status": "invalid", "directive": "", "path": str(path)})
            continue
        rows.append(
            {
                "id": mission.id,
                "status": mission.status.value,
                "directive": mission.directive,
                "objective": mission.objective or "",
                "sources": str(len(mission.sources)),
                "path": str(path),
            }
        )
    return rows


def _split_lines(value: str | None) -> list[str]:
    if not value:
        return []
    return [line.strip() for line in value.splitlines() if line.strip()]


def _source_id(source_type: SourceType, locator: str, existing: Iterable[Source]) -> str:
    base = source_type.value.replace("_", "-")
    used = {source.id for source in existing}
    number = 1
    candidate = f"{base}-{number}"
    while candidate in used:
        number += 1
        candidate = f"{base}-{number}"
    return candidate


def add_source(mission: Mission, source_type: str, locator: str, access: str = "read") -> Source:
    locator = locator.strip()
    if not locator:
        raise ValueError("source locator must not be empty")
    kind = SourceType(source_type)
    mode = AccessMode(access)
    source = Source(id=_source_id(kind, locator, mission.sources), type=kind, locator=locator, access=mode)
    mission.sources.append(source)
    return source


def save_mission(root: Path, mission: Mission) -> Path:
    errors = mission.validate()
    if errors:
        raise ValueError("; ".join(errors))
    path = missions_dir(root) / f"{mission.id}.json"
    mission.write(path)
    return path


def mark_ready(mission: Mission) -> None:
    errors = mission.validate()
    if errors:
        raise ValueError("; ".join(errors))
    if not mission.objective:
        raise ValueError("objective is required before marking a mission ready")
    mission.status = MissionStatus.READY


def _mission_summary(mission: Mission) -> str:
    return json.dumps(mission.to_dict(), indent=2)


def _edit_sources(mission: Mission) -> None:
    from .interactive import ask, choose, confirm, show

    while True:
        current = "\n".join(f"{s.id}: {s.type.value} [{s.access.value}] {s.locator}" for s in mission.sources) or "No sources yet."
        action = choose(
            "Mission sources",
            current,
            [("add", "Add source"), ("remove", "Remove source"), ("done", "Done")],
        )
        if action in {None, "done"}:
            return
        if action == "add":
            source_type = choose(
                "Add mission source",
                "Source type",
                [(value.value, value.value.replace("_", " ").title()) for value in SourceType],
            )
            if not source_type:
                continue
            locator = ask("Add mission source", "Path, repository/ref, Drive locator, or URL", "")
            if not locator:
                continue
            access = choose(
                "Add mission source",
                "Allowed access",
                [("read", "Read only"), ("propose_write", "May propose writes"), ("write", "Write allowed")],
            ) or "read"
            try:
                add_source(mission, source_type, locator, access)
            except ValueError as exc:
                show("Mission source", str(exc))
        elif action == "remove" and mission.sources:
            source_id = choose(
                "Remove mission source",
                "Select source",
                [(source.id, f"{source.type.value}: {source.locator}") for source in mission.sources],
            )
            if source_id and confirm("Remove source", f"Remove {source_id}?"):
                mission.sources = [source for source in mission.sources if source.id != source_id]


def _edit_capabilities(mission: Mission) -> None:
    from .interactive import ask, choose, confirm

    caps = mission.capabilities
    workspace = choose(
        "Mission capabilities",
        "Canonical workspace access",
        [("read", "Read only"), ("propose_write", "Propose writes"), ("write", "Write")],
    )
    network = choose(
        "Mission capabilities",
        "Network access",
        [("none", "None"), ("brokered", "Brokered"), ("unrestricted", "Unrestricted")],
    )
    shell = choose(
        "Mission capabilities",
        "Shell access",
        [("none", "None"), ("restricted", "Restricted"), ("unrestricted", "Unrestricted")],
    )
    max_minions_text = ask("Mission capabilities", "Maximum minions", str(caps.max_minions))
    try:
        max_minions = max(0, int(max_minions_text or caps.max_minions))
    except ValueError:
        max_minions = caps.max_minions
    mission.capabilities = CapabilitySet(
        canonical_workspace=AccessMode(workspace or caps.canonical_workspace.value),
        scratch_write=confirm("Mission capabilities", "Allow scratch writes?"),
        git_inspect=confirm("Mission capabilities", "Allow Git inspection?"),
        git_propose_commit=confirm("Mission capabilities", "Allow proposing commits?"),
        git_push=confirm("Mission capabilities", "Allow Git push?"),
        network=network or caps.network,
        shell=shell or caps.shell,
        max_minions=max_minions,
    )


def edit_mission_interactive(root: Path, mission: Mission) -> Mission:
    from .interactive import ask, choose, show

    while True:
        action = choose(
            "Mission Builder",
            f"{mission.id} — {mission.status.value}\n{mission.directive}",
            [
                ("directive", "Mission prompt / directive"),
                ("objective", "Primary objective"),
                ("sources", f"Source documents ({len(mission.sources)})"),
                ("requirements", f"Requirements / constraints ({len(mission.requirements)})"),
                ("notes", f"Human notes ({len(mission.human_notes)})"),
                ("capabilities", "Capability bounds"),
                ("review", "Review normalized mission"),
                ("ready", "Validate and mark ready"),
                ("save", "Save draft"),
                ("done", "Save and return"),
            ],
        )
        if action is None:
            return mission
        if action == "directive":
            value = ask("Mission prompt", "Human directive", mission.directive)
            if value:
                mission.directive = value.strip()
        elif action == "objective":
            value = ask("Mission objective", "Primary objective", mission.objective or "")
            mission.objective = value.strip() if value else None
        elif action == "sources":
            _edit_sources(mission)
        elif action == "requirements":
            value = ask("Mission requirements", "One requirement or constraint per line", "\n".join(mission.requirements))
            if value is not None:
                mission.requirements = _split_lines(value)
        elif action == "notes":
            value = ask("Mission notes", "One note per line", "\n".join(mission.human_notes))
            if value is not None:
                mission.human_notes = _split_lines(value)
        elif action == "capabilities":
            _edit_capabilities(mission)
        elif action == "review":
            show("Mission review", _mission_summary(mission)[:12000])
        elif action == "ready":
            try:
                mark_ready(mission)
                path = save_mission(root, mission)
                show("Mission ready", f"Validated and saved:\n{path}")
            except ValueError as exc:
                show("Mission not ready", str(exc))
        elif action in {"save", "done"}:
            try:
                path = save_mission(root, mission)
                if action == "save":
                    show("Mission saved", str(path))
                else:
                    return mission
            except ValueError as exc:
                show("Mission validation", str(exc))


def create_mission_interactive(root: Path, actor: str = "human:user") -> Path | None:
    from .interactive import ask, show

    directive = ask("Create mission", "Mission prompt / directive", "")
    if not directive:
        return None
    mission = Mission.draft(directive=directive, workspace=str(root.resolve()), actor_id=actor)
    edit_mission_interactive(root, mission)
    try:
        return save_mission(root, mission)
    except ValueError as exc:
        show("Mission validation", str(exc))
        return None


def mission_menu(root: Path) -> None:
    from .interactive import choose, show

    root = root.resolve()
    while True:
        rows = list_missions(root)
        action = choose(
            "Missions",
            f"Project: {root}\n{len(rows)} mission(s)",
            [("create", "Create mission"), ("edit", "Edit / resume mission"), ("review", "Review mission"), ("list", "List missions"), ("back", "Back")],
        )
        if action in {None, "back"}:
            return
        if action == "create":
            create_mission_interactive(root)
        elif action == "list":
            show("Missions", json.dumps(rows, indent=2)[:12000])
        elif action in {"edit", "review"}:
            if not rows:
                show("Missions", "No missions exist yet.")
                continue
            mission_id = choose("Missions", "Select mission", [(row["id"], f"{row['status']}: {row['directive']}") for row in rows])
            if not mission_id:
                continue
            mission = Mission.read(mission_path(root, mission_id))
            if action == "edit":
                edit_mission_interactive(root, mission)
            else:
                show("Mission review", _mission_summary(mission)[:12000])


def run_home_menu(root: Path | None = None) -> int:
    from .interactive import ask, choose, show
    from .cli import cmd_agent_chat, main as cli_main

    root = (root or Path.cwd()).resolve()
    while True:
        action = choose(
            "Dreadnought",
            f"Project: {root}",
            [
                ("missions", "Missions"),
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
        if action == "missions":
            mission_menu(root)
        elif action == "init":
            cli_main(["init", "--root", str(root)])
        elif action == "chat":
            rc = cmd_agent_chat(type("Args", (), {"root": str(root), "agent_type": None})())
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
