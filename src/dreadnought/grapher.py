from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any

from .protocol import ProtocolRecord


CONTROL_PLANE_ACTOR = "dreadnought:control-plane"


@dataclass
class GrapherWriteResult:
    record_id: str
    graph_path: Path
    history_path: Path


class GrapherControlPlane:
    """Privileged adapter that projects validated protocol records into Grapher.

    Agents submit ProtocolRecord objects to Dreadnought. Only this adapter writes the
    canonical `.grapher` state. OS-level enforcement arrives with the Sarcophagus; this
    module establishes the software authority boundary first.
    """

    def __init__(self, workspace: Path | str):
        self.workspace = Path(workspace)
        self.grapher_dir = self.workspace / ".grapher"
        self.graph_path = self.grapher_dir / "knowledge.json"
        self.history_path = self.grapher_dir / "history.jsonl"

    def write_record(self, record: ProtocolRecord) -> GrapherWriteResult:
        errors = record.validate()
        if errors:
            raise ValueError("invalid protocol record: " + "; ".join(errors))

        graph = self._load_graph()
        nodes = graph.setdefault("nodes", {})
        if record.id in nodes:
            raise ValueError(f"record already exists: {record.id}")

        node = self._node_from_record(record)
        nodes[record.id] = node
        self._append_reference_edges(graph, record)

        now = datetime.now(timezone.utc).isoformat()
        graph.setdefault("graph", {})["updated_at"] = now
        self._atomic_write_json(self.graph_path, graph)
        self._append_history(record, now)
        return GrapherWriteResult(record.id, self.graph_path, self.history_path)

    def _load_graph(self) -> dict[str, Any]:
        if not self.graph_path.exists():
            raise FileNotFoundError(f"Grapher graph not initialized: {self.graph_path}")
        graph = json.loads(self.graph_path.read_text())
        if graph.get("version") != 2:
            raise ValueError("unsupported Grapher graph version")
        if not isinstance(graph.get("nodes"), dict) or not isinstance(graph.get("edges"), list):
            raise ValueError("malformed Grapher graph")
        return graph

    def _node_from_record(self, record: ProtocolRecord) -> dict[str, Any]:
        payload = record.to_dict()
        title = f"{record.kind.value}: {record.subject_ref or record.id}"
        content = json.dumps(record.data, sort_keys=True)
        return {
            "id": record.id,
            "type": record.kind.value,
            "title": title,
            "content": content,
            "path": ".grapher/history.jsonl",
            "tags": ["dreadnought-protocol", record.perspective.value, record.kind.value],
            "meta": {
                "schema_version": record.schema_version,
                "mission_ref": record.mission_ref,
                "doctrine_ref": record.doctrine_ref,
                "order_ref": record.order_ref,
                "subject_ref": record.subject_ref,
                "evidence_refs": record.evidence_refs,
                "protocol": payload,
            },
            "created_at": record.created_at,
            "updated_at": record.created_at,
            "status": "current",
            "workflow_state": "active",
            "verification": "unverified",
            "stage": "developing",
            "evidence": [{"type": "protocol_record", "ref": record.id}],
            "source_refs": [ref for ref in (record.mission_ref, record.doctrine_ref, record.order_ref) if ref],
            "owners": [record.actor_id],
            "scope": {"project_id": "dreadnought"},
            "provenance": {
                "actor_id": CONTROL_PLANE_ACTOR,
                "actor_kind": "control_plane",
                "source": "dreadnought-protocol",
                "integrity": "observed-write",
                "submitted_by": record.actor_id,
                "submitted_perspective": record.perspective.value,
                "recorded_at": datetime.now(timezone.utc).isoformat(),
            },
        }

    def _append_reference_edges(self, graph: dict[str, Any], record: ProtocolRecord) -> None:
        edges = graph["edges"]
        now = datetime.now(timezone.utc).isoformat()
        refs = [
            (record.subject_ref, "about"),
            (record.mission_ref, "part_of_mission"),
            (record.doctrine_ref, "derived_from_doctrine"),
            (record.order_ref, "part_of_order"),
        ]
        refs.extend((ref, "supported_by") for ref in record.evidence_refs)
        for target, relation in refs:
            if target:
                edges.append({"from": record.id, "to": target, "rel": relation, "created_at": now})

    def _append_history(self, record: ProtocolRecord, recorded_at: str) -> None:
        self.grapher_dir.mkdir(parents=True, exist_ok=True)
        event = {
            "event": "protocol_record_written",
            "record_id": record.id,
            "kind": record.kind.value,
            "perspective": record.perspective.value,
            "submitted_by": record.actor_id,
            "writer": CONTROL_PLANE_ACTOR,
            "recorded_at": recorded_at,
        }
        with self.history_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(event, sort_keys=True) + "\n")

    @staticmethod
    def _atomic_write_json(path: Path, payload: dict[str, Any]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(path.suffix + ".tmp")
        tmp.write_text(json.dumps(payload, indent=2) + "\n")
        tmp.replace(path)
