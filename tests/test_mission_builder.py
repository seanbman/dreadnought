from pathlib import Path

import pytest

from dreadnought.mission import Mission
from dreadnought.mission_builder import add_source, list_missions, mark_ready, save_mission


def test_builder_persists_sources_requirements_and_ready_state(tmp_path: Path) -> None:
    mission = Mission.draft("Ship the bounded change", str(tmp_path), "human:user")
    mission.objective = "Implement and verify the requested feature"
    mission.requirements = ["Preserve existing CLI compatibility", "Use source documents as evidence"]
    mission.human_notes = ["Human acceptance remains authoritative"]
    source = add_source(mission, "file", "docs/spec.md", "read")
    assert source.id == "file-1"

    mark_ready(mission)
    path = save_mission(tmp_path, mission)
    loaded = Mission.read(path)

    assert loaded.status.value == "ready"
    assert loaded.objective == mission.objective
    assert loaded.requirements == mission.requirements
    assert loaded.sources[0].locator == "docs/spec.md"
    assert list_missions(tmp_path)[0]["id"] == mission.id


def test_ready_requires_objective(tmp_path: Path) -> None:
    mission = Mission.draft("Do the work", str(tmp_path), "human:user")
    with pytest.raises(ValueError, match="objective"):
        mark_ready(mission)
