import json
from pathlib import Path

from grapher.store import init_store

from dreadnought.bootstrap import bootstrap_workspace, discover_project_roots
from dreadnought.grapher import GrapherControlPlane
from dreadnought.mission import Mission


def _legacy_graph(project: Path) -> None:
    graph_path = project / ".grapher" / "knowledge.json"
    init_store(graph_path, name="legacy", domain="software", profile="software")
    graph = json.loads(graph_path.read_text())
    graph["nodes"]["legacy-unclassified"] = {
        "id": "legacy-unclassified",
        "type": "knowledge",
        "title": "Inherited fact",
        "content": "Legacy provenance must survive adoption.",
        "status": "unclassified",
    }
    graph_path.write_text(json.dumps(graph, indent=2) + "\n")
    config_path = project / ".grapher" / "config.json"
    config = json.loads(config_path.read_text())
    config["custom_node_types"] = ["legacy_custom"]
    config_path.write_text(json.dumps(config, indent=2) + "\n")


def test_adopt_existing_graph_preserves_nodes_and_grandfathers_legacy_status(tmp_path: Path) -> None:
    _legacy_graph(tmp_path)
    before = json.loads((tmp_path / ".grapher" / "knowledge.json").read_text())

    result = GrapherControlPlane(tmp_path).adopt()

    after = json.loads((tmp_path / ".grapher" / "knowledge.json").read_text())
    config = json.loads((tmp_path / ".grapher" / "config.json").read_text())
    assert after == before
    assert result["mode"] == "adopted"
    assert result["legacy_unclassified_allowlisted"] == 1
    assert "legacy-unclassified" in config["truth_status_legacy_allowlist"]
    assert "legacy_custom" in config["custom_node_types"]
    assert "dreadnought_claim" in config["custom_node_types"]
    assert config["require_explicit_status"] is True
    assert GrapherControlPlane(tmp_path).doctor()["compatible"] is True


def test_workspace_config_routes_control_plane_to_nested_project(tmp_path: Path) -> None:
    project = tmp_path / "pt-site-overhaul"
    project.mkdir()
    _legacy_graph(project)
    config_dir = tmp_path / ".dreadnought"
    config_dir.mkdir()
    (config_dir / "config.json").write_text(
        json.dumps({"version": 1, "project_id": "pt-site-overhaul", "project_root": "pt-site-overhaul"})
    )

    plane = GrapherControlPlane(tmp_path)

    assert plane.project_root == project.resolve()
    assert plane.graph_path == project / ".grapher" / "knowledge.json"


def test_bootstrap_adopts_nested_project_and_generates_instructions(tmp_path: Path) -> None:
    project = tmp_path / "pt-site-overhaul"
    project.mkdir()
    (project / ".git").mkdir()
    _legacy_graph(project)

    result = bootstrap_workspace(
        tmp_path,
        directive="Continue the Plumbing Track site overhaul under Dreadnought control.",
        objective="Adopt the existing project brain and continue development without rewriting history.",
        requirements=["Dreadnought is the sole Grapher writer."],
    )

    config = json.loads((tmp_path / ".dreadnought" / "config.json").read_text())
    mission = Mission.read(Path(result["mission_path"]))
    instructions = Path(result["instructions"]).read_text()
    agent_entry = (tmp_path / "AGENTS.md").read_text()
    graph = json.loads((project / ".grapher" / "knowledge.json").read_text())

    assert config["project_root"] == "pt-site-overhaul"
    assert config["bootstrap_mission"] == mission.id
    assert mission.status.value == "ready"
    assert mission.sources[0].locator == str(project.resolve())
    assert result["brain"]["mode"] == "adopted"
    assert "Continue the Plumbing Track site overhaul" in instructions
    assert "sole authority that mutates Grapher" in instructions
    assert ".dreadnought/INSTRUCTIONS.md" in agent_entry
    assert "legacy-unclassified" in graph["nodes"]
    assert GrapherControlPlane(tmp_path).doctor()["compatible"] is True


def test_bootstrap_initializes_new_workspace_when_no_project_exists(tmp_path: Path) -> None:
    assert discover_project_roots(tmp_path) == []

    result = bootstrap_workspace(tmp_path, directive="Create a new managed project context.")

    assert result["brain"]["mode"] == "initialized"
    assert (tmp_path / ".grapher" / "knowledge.json").is_file()
    assert Path(result["instructions"]).is_file()
