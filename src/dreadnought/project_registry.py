from __future__ import annotations

from dataclasses import dataclass, asdict
from pathlib import Path
import re
from typing import Any

from .config import load_config, save_config


_ID_RE = re.compile(r"^[a-z0-9][a-z0-9._-]*$")


@dataclass(frozen=True)
class ProjectRecord:
    id: str
    root: str
    directive: str | None = None
    docs_root: str | None = None
    managed: bool = False

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _project_ref(workspace: Path, project_root: Path) -> str:
    workspace = workspace.resolve()
    project_root = project_root.resolve()
    try:
        relative = project_root.relative_to(workspace)
    except ValueError as exc:
        raise ValueError("project root must be inside the Dreadnought workspace") from exc
    return "." if relative == Path(".") else str(relative)


def _resolve_ref(workspace: Path, value: str) -> Path:
    candidate = Path(value)
    if not candidate.is_absolute():
        candidate = workspace / candidate
    return candidate.resolve()


def _normalize_id(project_id: str) -> str:
    value = project_id.strip().lower()
    if not _ID_RE.fullmatch(value):
        raise ValueError("project id must use lowercase letters, digits, '.', '_' or '-' and start with a letter or digit")
    return value


def _migrate_legacy(config: dict[str, Any], workspace: Path) -> bool:
    projects = dict(config.get("projects") or {})
    if projects or not config.get("project_root"):
        config["projects"] = projects
        return False

    project_id = _normalize_id(str(config.get("project_id") or workspace.name))
    projects[project_id] = ProjectRecord(
        id=project_id,
        root=str(config["project_root"]),
        directive=None,
        docs_root=None,
        managed=False,
    ).to_dict()
    config["projects"] = projects
    config["active_project"] = project_id
    return True


def _sync_legacy_aliases(config: dict[str, Any], workspace: Path) -> None:
    projects = dict(config.get("projects") or {})
    active = config.get("active_project")
    if active and active in projects:
        record = projects[active]
        config["project_id"] = active
        config["project_root"] = record["root"]
    elif projects:
        first = sorted(projects)[0]
        config["active_project"] = first
        config["project_id"] = first
        config["project_root"] = projects[first]["root"]
    else:
        config["active_project"] = None
        config["project_id"] = workspace.name
        config.pop("project_root", None)


def register_project(
    workspace: Path | str,
    project_root: Path | str,
    *,
    project_id: str | None = None,
    directive: str | None = None,
    docs_root: str | None = None,
    managed: bool = False,
    make_default: bool | None = None,
) -> ProjectRecord:
    workspace = Path(workspace).resolve()
    root = Path(project_root)
    if not root.is_absolute():
        root = workspace / root
    root = root.resolve()
    if not root.is_dir():
        raise ValueError(f"project root does not exist: {root}")

    ref = _project_ref(workspace, root)
    project_id = _normalize_id(project_id or root.name or workspace.name)
    config = load_config(workspace)
    _migrate_legacy(config, workspace)
    projects = dict(config.get("projects") or {})

    existing = projects.get(project_id)
    if existing and str(existing.get("root")) != ref:
        raise ValueError(f"project id already registered: {project_id}")
    for other_id, other in projects.items():
        if other_id != project_id and str(other.get("root")) == ref:
            raise ValueError(f"project root already registered as {other_id}: {root}")

    record = ProjectRecord(
        id=project_id,
        root=ref,
        directive=(directive or "").strip() or None,
        docs_root=(docs_root or "").strip() or None,
        managed=bool(managed),
    )
    projects[project_id] = record.to_dict()
    config["projects"] = projects
    if make_default is True or (make_default is None and not config.get("active_project")):
        config["active_project"] = project_id
    _sync_legacy_aliases(config, workspace)
    save_config(workspace, config)
    return record


def list_projects(workspace: Path | str) -> list[dict[str, Any]]:
    workspace = Path(workspace).resolve()
    config = load_config(workspace)
    changed = _migrate_legacy(config, workspace)
    _sync_legacy_aliases(config, workspace)
    if changed:
        save_config(workspace, config)
    active = config.get("active_project")
    return [
        {**dict(config["projects"][project_id]), "active": project_id == active}
        for project_id in sorted(config.get("projects") or {})
    ]


def get_project(workspace: Path | str, project_id: str | None = None) -> ProjectRecord:
    workspace = Path(workspace).resolve()
    config = load_config(workspace)
    changed = _migrate_legacy(config, workspace)
    _sync_legacy_aliases(config, workspace)
    if changed:
        save_config(workspace, config)
    selected = _normalize_id(project_id) if project_id else config.get("active_project")
    if not selected:
        raise ValueError("no project is registered")
    raw = (config.get("projects") or {}).get(selected)
    if not raw:
        raise ValueError(f"project is not registered: {selected}")
    return ProjectRecord(
        id=selected,
        root=str(raw["root"]),
        directive=raw.get("directive"),
        docs_root=raw.get("docs_root"),
        managed=bool(raw.get("managed")),
    )


def resolve_project_root(workspace: Path | str, project_id: str | None = None) -> Path:
    workspace = Path(workspace).resolve()
    record = get_project(workspace, project_id)
    root = _resolve_ref(workspace, record.root)
    if not root.is_dir():
        raise ValueError(f"registered project root is missing: {root}")
    return root


def select_project(workspace: Path | str, project_id: str) -> ProjectRecord:
    workspace = Path(workspace).resolve()
    record = get_project(workspace, project_id)
    config = load_config(workspace)
    _migrate_legacy(config, workspace)
    config["active_project"] = record.id
    _sync_legacy_aliases(config, workspace)
    save_config(workspace, config)
    return record


def unregister_project(workspace: Path | str, project_id: str) -> ProjectRecord:
    workspace = Path(workspace).resolve()
    project_id = _normalize_id(project_id)
    config = load_config(workspace)
    _migrate_legacy(config, workspace)
    projects = dict(config.get("projects") or {})
    raw = projects.pop(project_id, None)
    if raw is None:
        raise ValueError(f"project is not registered: {project_id}")
    config["projects"] = projects
    if config.get("active_project") == project_id:
        config["active_project"] = sorted(projects)[0] if projects else None
    _sync_legacy_aliases(config, workspace)
    save_config(workspace, config)
    return ProjectRecord(
        id=project_id,
        root=str(raw["root"]),
        directive=raw.get("directive"),
        docs_root=raw.get("docs_root"),
        managed=bool(raw.get("managed")),
    )
