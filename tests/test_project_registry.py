from pathlib import Path

from dreadnought.config import load_config, save_config
from dreadnought.project_registry import (
    get_project,
    list_projects,
    register_project,
    resolve_project_root,
    select_project,
    unregister_project,
)


def test_registry_manages_multiple_projects_without_deleting_files(tmp_path: Path) -> None:
    alpha = tmp_path / "alpha"
    beta = tmp_path / "beta"
    alpha.mkdir()
    beta.mkdir()

    register_project(tmp_path, alpha, project_id="alpha", directive="Build alpha")
    register_project(tmp_path, beta, project_id="beta", directive="Build beta")

    projects = list_projects(tmp_path)
    assert [item["id"] for item in projects] == ["alpha", "beta"]
    assert projects[0]["active"] is True
    assert projects[1]["active"] is False

    select_project(tmp_path, "beta")
    assert get_project(tmp_path).id == "beta"
    assert resolve_project_root(tmp_path) == beta.resolve()

    removed = unregister_project(tmp_path, "beta")
    assert removed.id == "beta"
    assert beta.is_dir()
    assert get_project(tmp_path).id == "alpha"


def test_registry_rejects_duplicate_root_and_outside_workspace(tmp_path: Path) -> None:
    alpha = tmp_path / "alpha"
    alpha.mkdir()
    register_project(tmp_path, alpha, project_id="alpha")

    try:
        register_project(tmp_path, alpha, project_id="other")
    except ValueError as exc:
        assert "already registered" in str(exc)
    else:
        raise AssertionError("duplicate project root should be rejected")

    outside = tmp_path.parent / "outside-project"
    outside.mkdir(exist_ok=True)
    try:
        register_project(tmp_path, outside, project_id="outside")
    except ValueError as exc:
        assert "inside the Dreadnought workspace" in str(exc)
    else:
        raise AssertionError("outside project root should be rejected")


def test_registry_migrates_legacy_single_project_config(tmp_path: Path) -> None:
    project = tmp_path / "legacy"
    project.mkdir()
    config = load_config(tmp_path)
    config["version"] = 1
    config["project_id"] = "legacy"
    config["project_root"] = "legacy"
    config.pop("projects", None)
    config.pop("active_project", None)
    save_config(tmp_path, config)

    projects = list_projects(tmp_path)
    assert len(projects) == 1
    assert projects[0]["id"] == "legacy"
    assert projects[0]["root"] == "legacy"
    assert projects[0]["active"] is True
