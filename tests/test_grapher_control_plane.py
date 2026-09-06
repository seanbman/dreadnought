import json
from pathlib import Path

import pytest

from dreadnought.grapher import CONTROL_PLANE_ACTOR, GrapherControlPlane
from dreadnought.protocol import Perspective, Predicate, ProtocolRecord, RecordKind


def initialized_workspace(tmp_path: Path) -> Path:
    graph_dir = tmp_path / ".grapher"
    graph_dir.mkdir()
    (graph_dir / "knowledge.json").write_text(json.dumps({
        "version": 2,
        "graph": {"name": "test", "domain": "test", "updated_at": "2026-09-06T00:00:00+00:00"},
        "nodes": {},
        "edges": [],
    }))
    return tmp_path


def test_agent_claim_is_written_by_control_plane(tmp_path: Path) -> None:
    workspace = initialized_workspace(tmp_path)
    record = ProtocolRecord.claim(
        actor_id="agent:arm-1",
        subject_ref="artifact:file-a",
        predicate=Predicate.EXISTS,
        order_ref="order-1",
    )

    result = GrapherControlPlane(workspace).write_record(record)

    graph = json.loads(result.graph_path.read_text())
    node = graph["nodes"][record.id]
    assert node["provenance"]["actor_id"] == CONTROL_PLANE_ACTOR
    assert node["provenance"]["submitted_by"] == "agent:arm-1"
    assert node["meta"]["protocol"]["perspective"] == "agent"
    assert any(edge["rel"] == "part_of_order" for edge in graph["edges"])
    history = [json.loads(line) for line in result.history_path.read_text().splitlines()]
    assert history[-1]["record_id"] == record.id


def test_invalid_record_is_rejected_before_graph_mutation(tmp_path: Path) -> None:
    workspace = initialized_workspace(tmp_path)
    record = ProtocolRecord.create(
        kind=RecordKind.OBSERVATION,
        perspective=Perspective.AGENT,
        actor_id="agent:arm-1",
        data={"observation_type": "test", "result": "passed"},
    )

    with pytest.raises(ValueError, match="invalid protocol record"):
        GrapherControlPlane(workspace).write_record(record)

    graph = json.loads((workspace / ".grapher" / "knowledge.json").read_text())
    assert graph["nodes"] == {}


def test_duplicate_record_is_rejected(tmp_path: Path) -> None:
    workspace = initialized_workspace(tmp_path)
    record = ProtocolRecord.claim(
        actor_id="agent:arm-1",
        subject_ref="artifact:file-a",
        predicate=Predicate.EXISTS,
    )
    store = GrapherControlPlane(workspace)
    store.write_record(record)

    with pytest.raises(ValueError, match="record already exists"):
        store.write_record(record)
