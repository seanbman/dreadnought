from __future__ import annotations

from pathlib import Path
import re
import shutil
import subprocess
from typing import Any

from .grapher import GrapherControlPlane
from .mission import AccessMode, Mission, MissionStatus, Source, SourceType
from .project_registry import register_project


_GENERATED_MARKER = "<!-- dreadnought:generated-project -->"


def project_slug(name: str) -> str:
    value = re.sub(r"[^a-z0-9]+", "-", name.strip().lower()).strip("-")
    if not value:
        raise ValueError("project name must contain at least one letter or digit")
    return value


def _write_project_instructions(project_root: Path, *, name: str, directive: str, mission_id: str, docs_root: str) -> Path:
    path = project_root / ".dreadnought" / "PROJECT_INSTRUCTIONS.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        f"""# {name} — Dreadnought project instructions

{_GENERATED_MARKER}

## Project identity

- Project root: `{project_root}`
- Initial mission: `{mission_id}`
- Documentation root: `{docs_root}`

## Operator directive

{directive}

## Authority

- This project is managed by the enclosing Dreadnought workspace.
- Grapher is this project's durable brain.
- Within Dreadnought control, only Dreadnought mutates `.grapher/`.
- Project Arms and Sarcophagus agents receive brokered context and return typed testimony; they do not write Grapher directly.
- Git history, project documentation, and Grapher provenance must remain consistent with verified work.

## Working rule

Read the project documentation and relevant Grapher context before planning work. Treat inherited or external documentation as evidence, not as automatically current truth. Record durable decisions and verified state through Dreadnought.
""",
        encoding="utf-8",
    )
    return path


def _write_project_entrypoints(project_root: Path, *, name: str, directive: str) -> None:
    (project_root / "README.md").write_text(
        f"# {name}\n\n{directive}\n\nManaged by Dreadnought. See `.dreadnought/PROJECT_INSTRUCTIONS.md` before executing project work.\n",
        encoding="utf-8",
    )
    (project_root / "AGENTS.md").write_text(
        f"{_GENERATED_MARKER}\n# Dreadnought project entrypoint\n\nRead `.dreadnought/PROJECT_INSTRUCTIONS.md` before planning or executing work.\n",
        encoding="utf-8",
    )


def _write_initial_mission(workspace: Path, project_root: Path, *, directive: str, actor: str) -> Mission:
    mission = Mission.draft(directive=directive, workspace=str(workspace), actor_id=actor)
    mission.objective = directive
    mission.sources.append(
        Source(id="project-1", type=SourceType.WORKSPACE, locator=str(project_root), access=AccessMode.READ)
    )
    mission.requirements = [
        "Preserve Dreadnought as the project control plane and Grapher as the durable project brain."
    ]
    mission.human_notes.append(f"Created project: {project_root.name}")
    mission.status = MissionStatus.READY
    errors = mission.validate()
    if errors:
        raise ValueError("invalid initial project mission: " + "; ".join(errors))
    mission.write(workspace / ".dreadnought" / "missions" / f"{mission.id}.json")
    return mission


def create_project(
    workspace: Path | str,
    name: str,
    directive: str,
    *,
    project_id: str | None = None,
    docs_source: Path | str | None = None,
    actor: str = "human:user",
    make_default: bool | None = None,
) -> dict[str, Any]:
    workspace = Path(workspace).resolve()
    workspace.mkdir(parents=True, exist_ok=True)
    directive = directive.strip()
    if not directive:
        raise ValueError("project directive must not be empty")

    slug = project_slug(project_id or name)
    project_root = workspace / slug
    if project_root.exists():
        raise ValueError(f"project path already exists: {project_root}")

    linked_docs: Path | None = None
    if docs_source is not None:
        linked_docs = Path(docs_source).expanduser().resolve()
        if not linked_docs.is_dir():
            raise ValueError(f"documentation source does not exist or is not a directory: {linked_docs}")

    project_root.mkdir(parents=False)
    try:
        try:
            subprocess.run(
                ["git", "init"],
                cwd=project_root,
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
        except (FileNotFoundError, subprocess.CalledProcessError) as exc:
            raise RuntimeError(f"git init failed for {project_root}: {exc}") from exc

        docs_path = project_root / "docs"
        if linked_docs is None:
            docs_path.mkdir()
            docs_root_value = "docs"
        else:
            docs_path.symlink_to(linked_docs, target_is_directory=True)
            docs_root_value = str(linked_docs)

        mission = _write_initial_mission(workspace, project_root, directive=directive, actor=actor)
        _write_project_entrypoints(project_root, name=name.strip() or slug, directive=directive)
        instructions = _write_project_instructions(
            project_root,
            name=name.strip() or slug,
            directive=directive,
            mission_id=mission.id,
            docs_root=docs_root_value,
        )

        plane = GrapherControlPlane(project_root)
        graph_path = plane.initialize()
        doctor = plane.doctor()
        if not doctor.get("compatible"):
            raise RuntimeError("new project Grapher brain failed compatibility checks")

        record = register_project(
            workspace,
            project_root,
            project_id=slug,
            directive=directive,
            docs_root=docs_root_value,
            managed=True,
            make_default=make_default,
        )
        return {
            "project": record.to_dict(),
            "root": str(project_root),
            "git": str(project_root / ".git"),
            "docs": str(docs_path),
            "docs_linked": linked_docs is not None,
            "instructions": str(instructions),
            "mission": mission.id,
            "graph": str(graph_path),
            "grapher": doctor,
        }
    except Exception:
        shutil.rmtree(project_root, ignore_errors=True)
        raise
