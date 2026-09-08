from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
from typing import Any

import grapher as grapher_package
from grapher.config import load_config, save_config
from grapher.integrations import embedded as grapher

from .protocol import ProtocolRecord


CONTROL_PLANE_ACTOR = "dreadnought:control-plane"

_REQUIRED_NODE_TYPES = {
    "dreadnought_claim",
    "dreadnought_observation",
    "dreadnought_action",
    "dreadnought_artifact",
    "dreadnought_requirement",
    "dreadnought_risk",
    "dreadnought_note",
    "dreadnought_verdict",
}

_RELATION_MAP = {
    "subject": "references",
    "mission": "part_of",
    "doctrine": "derived_from",
    "order": "part_of",
    "evidence": "evidenced_by",
}


@dataclass
class GrapherWriteResult:
    record_id: str
    graph_path: Path
    history_path: Path


class GrapherControlPlane:
    """Exclusive Dreadnought write authority for one project Grapher brain.

    ``workspace`` is the enclosing Dreadnought workspace root. ``project_id`` may name
    any registered project without mutating the workspace default. If omitted, the
    selected default project's compatibility route is used. A standalone project root
    without Dreadnought workspace configuration still resolves to itself.
    """

    def __init__(
        self,
        workspace: Path | str,
        *,
        project_id: str | None = None,
        project_root: Path | str | None = None,
    ):
        self.workspace = Path(workspace).resolve()
        self.selected_project_id = project_id
        self.project_root = self._resolve_project_root(project_id=project_id, project_root=project_root)
        self.grapher_dir = self.project_root / ".grapher"
        self.graph_path = self.grapher_dir / "knowledge.json"
        self.history_path = self.grapher_dir / "history.jsonl"
        self.config_path = self.grapher_dir / "config.json"

    def _dreadnought_config(self) -> dict[str, Any]:
        path = self.workspace / ".dreadnought" / "config.json"
        if not path.is_file():
            return {}
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return {}
        return data if isinstance(data, dict) else {}

    def _resolve_project_root(
        self,
        *,
        project_id: str | None,
        project_root: Path | str | None,
    ) -> Path:
        if project_root is not None:
            candidate = Path(project_root)
            if not candidate.is_absolute():
                candidate = self.workspace / candidate
            return candidate.resolve()

        config = self._dreadnought_config()
        projects = dict(config.get("projects") or {})
        selected = project_id or config.get("active_project")
        if selected and selected in projects:
            raw = str(projects[selected].get("root") or "")
            if not raw:
                raise ValueError(f"registered project has no root: {selected}")
            candidate = Path(raw)
            if not candidate.is_absolute():
                candidate = self.workspace / candidate
            self.selected_project_id = str(selected)
            return candidate.resolve()
        if project_id:
            raise ValueError(f"project is not registered: {project_id}")

        raw = config.get("project_root")
        if not raw:
            return self.workspace
        candidate = Path(str(raw))
        if not candidate.is_absolute():
            candidate = self.workspace / candidate
        return candidate.resolve()

    def _project_id(self) -> str:
        if self.selected_project_id:
            return str(self.selected_project_id)
        config = self._dreadnought_config()
        return str(config.get("active_project") or config.get("project_id") or self.project_root.name or "dreadnought")

    def initialize(self) -> Path:
        if self.graph_path.exists():
            raise ValueError(f"Grapher graph already initialized: {self.graph_path}")

        grapher.init_context(
            self.graph_path,
            scope="project",
            name=self.project_root.name or "dreadnought-project",
            domain="agent-control-plane",
        )
        config = load_config(self.graph_path)
        config.update(
            {
                "profile": "software",
                "domain": "agent-control-plane",
                "kinds": [
                    "knowledge",
                    "implementation",
                    "decision",
                    "design",
                    "requirements",
                    "roadmap",
                    "retrospective",
                ],
                "stages": [
                    "ideation",
                    "designing",
                    "planning",
                    "developing",
                    "launching",
                    "maintaining",
                ],
                "custom_node_types": sorted(_REQUIRED_NODE_TYPES),
                "require_explicit_status": True,
                "truth_status_legacy_allowlist": [],
            }
        )
        save_config(self.graph_path, config)
        return self.graph_path

    def adopt(self) -> dict[str, Any]:
        if not self.graph_path.is_file():
            raise FileNotFoundError(f"Grapher graph not initialized: {self.graph_path}")
        try:
            graph = json.loads(self.graph_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise ValueError(f"cannot read Grapher graph: {exc}") from exc
        if not isinstance(graph, dict) or graph.get("version") != 2:
            raise ValueError("existing Grapher brain must be schema version 2 before Dreadnought adoption")

        nodes = graph.get("nodes") or {}
        if not isinstance(nodes, dict):
            raise ValueError("existing Grapher brain has invalid nodes collection")
        inherited_unclassified = {
            str(node_id)
            for node_id, node in nodes.items()
            if isinstance(node, dict) and (not node.get("status") or node.get("status") == "unclassified")
        }

        config = load_config(self.graph_path)
        configured_types = set(config.get("custom_node_types") or [])
        legacy_allowlist = set(config.get("truth_status_legacy_allowlist") or [])
        config["custom_node_types"] = sorted(configured_types | _REQUIRED_NODE_TYPES)
        config["require_explicit_status"] = True
        config["truth_status_legacy_allowlist"] = sorted(legacy_allowlist | inherited_unclassified)
        save_config(self.graph_path, config)

        checks = self.doctor()
        return {
            "mode": "adopted",
            "graph_path": str(self.graph_path),
            "graph_version": graph.get("version"),
            "existing_nodes": len(nodes),
            "legacy_unclassified_allowlisted": len(inherited_unclassified),
            "compatible": bool(checks.get("compatible")),
        }

    def doctor(self) -> dict[str, Any]:
        checks: dict[str, Any] = {
            "workspace": str(self.workspace),
            "project_id": self._project_id(),
            "project_root": str(self.project_root),
            "grapher_version": grapher_package.__version__,
            "embedded_api": callable(getattr(grapher, "contribute_context", None)),
            "graph_exists": self.graph_path.is_file(),
            "config_exists": self.config_path.is_file(),
        }
        if checks["graph_exists"]:
            try:
                graph = json.loads(self.graph_path.read_text(encoding="utf-8"))
                checks["graph_version"] = graph.get("version")
                checks["graph_v2"] = graph.get("version") == 2
            except (OSError, json.JSONDecodeError):
                checks["graph_v2"] = False
        else:
            checks["graph_v2"] = False

        if checks["config_exists"]:
            try:
                config = json.loads(self.config_path.read_text(encoding="utf-8"))
                configured_types = set(config.get("custom_node_types") or [])
                checks["explicit_truth_status"] = bool(config.get("require_explicit_status"))
                checks["projection_types"] = _REQUIRED_NODE_TYPES.issubset(configured_types)
            except (OSError, json.JSONDecodeError):
                checks["explicit_truth_status"] = False
                checks["projection_types"] = False
        else:
            checks["explicit_truth_status"] = False
            checks["projection_types"] = False

        required = (
            "embedded_api",
            "graph_exists",
            "config_exists",
            "graph_v2",
            "explicit_truth_status",
            "projection_types",
        )
        checks["compatible"] = all(bool(checks.get(key)) for key in required)
        return checks

    def write_record(self, record: ProtocolRecord) -> GrapherWriteResult:
        errors = record.validate()
        if errors:
            raise ValueError("invalid protocol record: " + "; ".join(errors))
        if not self.graph_path.exists():
            raise FileNotFoundError(f"Grapher graph not initialized: {self.graph_path}")
        if self._record_exists(record.id):
            raise ValueError(f"record already exists: {record.id}")

        payload = record.to_dict()
        grapher.contribute_context(
            self.graph_path,
            type=f"dreadnought_{record.kind.value}",
            title=f"{record.kind.value}: {record.subject_ref or record.id}",
            content=json.dumps(payload, sort_keys=True),
            node_id=record.id,
            path="dreadnought://protocol",
            tags=["dreadnought-protocol", record.perspective.value, record.kind.value],
            meta={
                "schema_version": record.schema_version,
                "protocol": payload,
                "submitted_by": record.actor_id,
                "submitted_perspective": record.perspective.value,
            },
            stage="developing",
            status="current",
            workflow_state="active",
            verification="unverified",
            evidence=[{"type": "protocol_record", "ref": record.id}],
            source_refs=[ref for ref in (record.mission_ref, record.doctrine_ref, record.order_ref) if ref],
            owners=[record.actor_id],
            scope=self._scope(record),
            provenance={
                "actor_id": CONTROL_PLANE_ACTOR,
                "actor_kind": "system_tool",
                "actor_role": "control-plane",
                "source": "dreadnought-protocol",
                "integrity": "declared",
            },
            actor={
                "id": CONTROL_PLANE_ACTOR,
                "kind": "system_tool",
                "role": "control-plane",
                "source": "dreadnought-protocol",
            },
            reason="Dreadnought admitted a validated protocol record",
            evidence_refs=list(record.evidence_refs),
            operation_id=record.id,
            phase="executed",
            source="dreadnought-control-plane",
        )
        self._link_existing_references(record)
        return GrapherWriteResult(record.id, self.graph_path, self.history_path)

    def query(self, text: str, *, limit: int = 10, mission: str | None = None) -> list[dict[str, Any]]:
        return grapher.query_context(self.graph_path, text, limit=limit, mission=mission)

    def get(self, node_id: str) -> dict[str, Any]:
        return grapher.get_context(self.graph_path, node_id)

    def _record_exists(self, record_id: str) -> bool:
        try:
            grapher.get_context(self.graph_path, record_id)
            return True
        except grapher.IntegrationError:
            return False

    def _scope(self, record: ProtocolRecord) -> dict[str, Any]:
        scope: dict[str, Any] = {"project_id": self._project_id()}
        if record.mission_ref:
            scope["mission_id"] = record.mission_ref
        return scope

    def _link_existing_references(self, record: ProtocolRecord) -> None:
        refs = [
            (record.subject_ref, _RELATION_MAP["subject"]),
            (record.mission_ref, _RELATION_MAP["mission"]),
            (record.doctrine_ref, _RELATION_MAP["doctrine"]),
            (record.order_ref, _RELATION_MAP["order"]),
        ]
        refs.extend((ref, _RELATION_MAP["evidence"]) for ref in record.evidence_refs)

        for target, relation in refs:
            if not target or not self._record_exists(target):
                continue
            grapher.link_context(
                self.graph_path,
                record.id,
                target,
                relation,
                actor={
                    "id": CONTROL_PLANE_ACTOR,
                    "kind": "system_tool",
                    "role": "control-plane",
                    "source": "dreadnought-protocol",
                },
                reason="Dreadnought projected a protocol reference",
                operation_id=f"{record.id}:{relation}:{target}",
                source="dreadnought-control-plane",
            )
