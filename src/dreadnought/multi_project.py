from __future__ import annotations

from pathlib import Path
from typing import Any, Iterable

from .grapher import GrapherControlPlane, GrapherWriteResult
from .project_registry import list_projects
from .protocol import ProtocolRecord


class MultiProjectControlPlane:
    """Address multiple registered projects in one Dreadnought control-plane session.

    Operations are synchronous and deterministic: project IDs are resolved once, then
    processed in sorted registry order without changing the workspace's selected
    default project. Each project keeps its own Grapher brain.
    """

    def __init__(self, workspace: Path | str):
        self.workspace = Path(workspace).resolve()

    def project_ids(self, requested: Iterable[str] | None = None) -> list[str]:
        registered = [str(item["id"]) for item in list_projects(self.workspace)]
        if requested is None:
            return registered
        wanted = list(dict.fromkeys(str(item) for item in requested))
        unknown = sorted(set(wanted) - set(registered))
        if unknown:
            raise ValueError("project is not registered: " + ", ".join(unknown))
        return [project_id for project_id in registered if project_id in wanted]

    def doctor(self, project_ids: Iterable[str] | None = None) -> dict[str, dict[str, Any]]:
        return {
            project_id: GrapherControlPlane(self.workspace, project_id=project_id).doctor()
            for project_id in self.project_ids(project_ids)
        }

    def query(
        self,
        text: str,
        *,
        project_ids: Iterable[str] | None = None,
        limit: int = 10,
        mission: str | None = None,
    ) -> dict[str, list[dict[str, Any]]]:
        return {
            project_id: GrapherControlPlane(self.workspace, project_id=project_id).query(
                text, limit=limit, mission=mission
            )
            for project_id in self.project_ids(project_ids)
        }

    def write_record(self, project_id: str, record: ProtocolRecord) -> GrapherWriteResult:
        self.project_ids([project_id])
        return GrapherControlPlane(self.workspace, project_id=project_id).write_record(record)

    def status(self, project_ids: Iterable[str] | None = None) -> dict[str, dict[str, Any]]:
        registry = {str(item["id"]): item for item in list_projects(self.workspace)}
        result: dict[str, dict[str, Any]] = {}
        for project_id in self.project_ids(project_ids):
            doctor = GrapherControlPlane(self.workspace, project_id=project_id).doctor()
            result[project_id] = {
                "project": registry[project_id],
                "grapher": doctor,
                "ready": bool(doctor.get("compatible")),
            }
        return result
