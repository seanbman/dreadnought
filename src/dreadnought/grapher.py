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
    """Exclusive Dreadnought write authority for an embedded Grapher brain.

    Project-arm agents submit typed ProtocolRecord testimony to Dreadnought. Dreadnought
    validates and projects that testimony, and this adapter is the only Dreadnought
    component permitted to mutate Grapher. Grapher remains responsible for canonical
    storage, truth policy, semantic integrity, transition handling, and history.
    """

    def __init__(self, workspace: Path | str):
        self.workspace = Path(workspace)
        self.grapher_dir = self.workspace / ".grapher"
        self.graph_path = self.grapher_dir / "knowledge.json"
        self.history_path = self.grapher_dir / "history.jsonl"
        self.config_path = self.grapher_dir / "config.json"

    def initialize(self) -> Path:
        """Initialize a new Dreadnought-managed Grapher context.

        Initialization is intentionally mediated by Dreadnought so a new workspace
        starts with the projection types and explicit truth-status policy required by
        the control plane. Existing graphs are never overwritten.
        """
        if self.graph_path.exists():
            raise ValueError(f"Grapher graph already initialized: {self.graph_path}")

        grapher.init_context(
            self.graph_path,
            scope="project",
            name=self.workspace.name or "dreadnought-project",
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

    def doctor(self) -> dict[str, Any]:
        """Return deterministic compatibility checks for the embedded Grapher brain."""
        checks: dict[str, Any] = {
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
            source_refs=[
                ref
                for ref in (record.mission_ref, record.doctrine_ref, record.order_ref)
                if ref
            ],
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
        """Read scoped brain context through the Dreadnought control plane."""
        return grapher.query_context(
            self.graph_path,
            text,
            limit=limit,
            mission=mission,
        )

    def get(self, node_id: str) -> dict[str, Any]:
        """Read a single Grapher node through the Dreadnought control plane."""
        return grapher.get_context(self.graph_path, node_id)

    def _record_exists(self, record_id: str) -> bool:
        try:
            grapher.get_context(self.graph_path, record_id)
            return True
        except grapher.IntegrationError:
            return False

    def _scope(self, record: ProtocolRecord) -> dict[str, Any]:
        scope: dict[str, Any] = {"project_id": "dreadnought"}
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
