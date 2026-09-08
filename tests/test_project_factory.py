import json
from pathlib import Path

from dreadnought.project_factory import create_project
from dreadnought.project_registry import get_project, list_projects


def test_create_project_builds_git_docs_grapher_instructions_and_mission(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    result = create_project(workspace, "New Service", "Build the bounded service")

    project = workspace / "new-service"
    assert project.is_dir()
    assert (project / ".git").is_dir()
    assert (project / "docs").is_dir()
    assert (project / "README.md").is_file()
    assert (project / "AGENTS.md").is_file()
    assert (project / ".dreadnought" / "PROJECT_INSTRUCTIONS.md").is_file()
    graph = json.loads((project / ".grapher" / "knowledge.json").read_text())
    assert graph["version"] == 2
    assert result["grapher"]["compatible"] is True
    assert (workspace / ".dreadnought" / "missions" / f"{result['mission']}.json").is_file()
    assert get_project(workspace, "new-service").managed is True


def test_create_project_can_link_existing_documentation_directory(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    docs_source = tmp_path / "existing-docs"
    docs_source.mkdir()
    (docs_source / "SPEC.md").write_text("authoritative source\n")

    result = create_project(
        workspace,
        "Linked Docs",
        "Use the supplied documentation as project evidence",
        docs_source=docs_source,
    )

    docs = workspace / "linked-docs" / "docs"
    assert docs.is_symlink()
    assert docs.resolve() == docs_source.resolve()
    assert (docs / "SPEC.md").read_text() == "authoritative source\n"
    assert result["docs_linked"] is True
    assert get_project(workspace, "linked-docs").docs_root == str(docs_source.resolve())


def test_created_projects_coexist_in_one_workspace(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    create_project(workspace, "Alpha", "Build alpha")
    create_project(workspace, "Beta", "Build beta")

    projects = list_projects(workspace)
    assert [item["id"] for item in projects] == ["alpha", "beta"]
    assert (workspace / "alpha" / ".grapher" / "knowledge.json").is_file()
    assert (workspace / "beta" / ".grapher" / "knowledge.json").is_file()
