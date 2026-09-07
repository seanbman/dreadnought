import json
from pathlib import Path

import pytest

from grapher.store import init_store, load_graph

from dreadnought.grapher import CONTROL_PLANE_ACTOR, GrapherControlPlane
from dreadnought.protocol import Perspective, Predicate, ProtocolRecord, RecordKind


def initialized_workspace(tmp_path: Path) -> Path:
    graph_path = tmp_path / ".grapher" / "knowledge.json"
    init_store(graph_path, name="test", domain="agent-control-plane", profile="software")
    return tmp_path


def configure_dreadnought_projection(workspace: Path) -> None:
    config_path = workspace / ".grapher" / "config.json"
    config = json.loads(config_path.read_text())
    config["require_explicit_status"] = True
    config["custom_node_types"] = [
        "dreadnought_claim",
        "dreadnought_observation",
        "dreadnought_action",
        "dreadnought_artifact",
        "dreadnought_requirement",
        "dreadnought_risk",
        "dreadnought_note",
        "dreadnought_verdict",
    ]
    config_path.write_text(json.dumps(config))


def test_grapher_initialize_creates_managed_brain(tmp_path: Path) -> None:
    plane = GrapherControlPlane(tmp_path)

    graph_path = plane.initialize()

    assert graph_path.is_file()
    config = json.loads((tmp_path / ".grapher" / "config.json").read_text())
    assert config["require_explicit_status"] is True
    assert "dreadnought_claim" in config["custom_node_types"]
    assert plane.doctor()["compatible"] is True


def test_grapher_initialize_refuses_existing_graph(tmp_path: Path) -> None:
    workspace = initialized_workspace(tmp_path)
    with pytest.raises(ValueError, match="already initialized"):
        GrapherControlPlane(workspace).initialize()


def test_grapher_doctor_reports_compatible_workspace(tmp_path: Path) -> None:
    workspace = initialized_workspace(tmp_path)
    configure_dreadnought_projection(workspace)

    checks = GrapherControlPlane(workspace).doctor()

    assert checks["embedded_api"] is True
    assert checks["graph_v2"] is True
    assert checks["explicit_truth_status"] is True
    assert checks["projection_types"] is True
    assert checks["compatible"] is True


def test_agent_claim_is_projected_by_control_plane(tmp_path: Path) -> None:
    workspace = initialized_workspace(tmp_path)
    record = ProtocolRecord.claim(
        actor_id="agent:arm-1",
        subject_ref="artifact:file-a",
        predicate=Predicate.EXISTS,
        order_ref="order-1",
    )

    result = GrapherControlPlane(workspace).write_record(record)

    graph = load_graph(result.graph_path)
    node = graph["nodes"][record.id]
    assert node["type"] == "dreadnought_claim"
    assert node["provenance"]["actor_id"] == CONTROL_PLANE_ACTOR
    assert node["provenance"]["actor_kind"] == "system_tool"
    assert node["provenance"]["integrity"] == "declared"
    assert node["meta"]["submitted_by"] == "agent:arm-1"
    assert node["meta"]["protocol"]["perspective"] == "agent"
    assert node["meta"]["protocol"] == record.to_dict()

    history = [json.loads(line) for line in result.history_path.read_text().splitlines()]
    assert history[-1]["action"] == "node_created"
    assert history[-1]["actor"]["id"] == CONTROL_PLANE_ACTOR
    assert history[-1]["source"] == "dreadnought-control-plane"
    assert history[-1]["operation_id"] == record.id


def test_control_plane_exposes_read_broker(tmp_path: Path) -> None:
    workspace = initialized_workspace(tmp_path)
    record = ProtocolRecord.claim(
        actor_id="dreadnought:observer",
        subject_ref="artifact:file-a",
        predicate=Predicate.EXISTS,
    )
    plane = GrapherControlPlane(workspace)
    plane.write_record(record)

    detail = plane.get(record.id)
    assert detail["node"]["id"] == record.id
    hits = plane.query("artifact:file-a")
    assert hits


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

    graph = load_graph(workspace / ".grapher" / "knowledge.json")
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
