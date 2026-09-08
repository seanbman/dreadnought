import json
from pathlib import Path

from grapher.store import load_graph

from dreadnought.config import load_config
from dreadnought.grapher import GrapherControlPlane
from dreadnought.multi_project import MultiProjectControlPlane
from dreadnought.project_factory import create_project
from dreadnought.protocol import Predicate, ProtocolRecord


def test_multi_project_control_addresses_all_brains_without_switching_default(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    create_project(workspace, "Alpha", "Build alpha")
    create_project(workspace, "Beta", "Build beta")
    assert load_config(workspace)["active_project"] == "alpha"

    control = MultiProjectControlPlane(workspace)
    status = control.status()

    assert list(status) == ["alpha", "beta"]
    assert status["alpha"]["ready"] is True
    assert status["beta"]["ready"] is True
    assert load_config(workspace)["active_project"] == "alpha"


def test_project_scoped_write_goes_only_to_named_brain(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    create_project(workspace, "Alpha", "Build alpha")
    create_project(workspace, "Beta", "Build beta")

    record = ProtocolRecord.claim(
        actor_id="dreadnought:test",
        subject_ref="artifact:beta-only",
        predicate=Predicate.EXISTS,
    )
    result = MultiProjectControlPlane(workspace).write_record("beta", record)

    beta = load_graph(workspace / "beta" / ".grapher" / "knowledge.json")
    alpha = load_graph(workspace / "alpha" / ".grapher" / "knowledge.json")
    assert result.graph_path == workspace / "beta" / ".grapher" / "knowledge.json"
    assert record.id in beta["nodes"]
    assert record.id not in alpha["nodes"]
    assert beta["nodes"][record.id]["scope"]["project_id"] == "beta"
    assert load_config(workspace)["active_project"] == "alpha"


def test_explicit_grapher_project_id_routes_without_mutating_default(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    create_project(workspace, "Alpha", "Build alpha")
    create_project(workspace, "Beta", "Build beta")

    plane = GrapherControlPlane(workspace, project_id="beta")
    assert plane.project_root == (workspace / "beta").resolve()
    assert plane.doctor()["project_id"] == "beta"
    assert load_config(workspace)["active_project"] == "alpha"
