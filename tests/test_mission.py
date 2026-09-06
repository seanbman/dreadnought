from pathlib import Path

from dreadnought.mission import Mission, MissionStatus


def test_draft_round_trip(tmp_path: Path) -> None:
    mission = Mission.draft(
        directive="Inspect the workspace and propose a patch.",
        workspace=str(tmp_path),
        actor_id="human:test",
    )
    assert mission.status is MissionStatus.DRAFT
    assert mission.validate() == []

    path = tmp_path / "mission.json"
    mission.write(path)
    loaded = Mission.read(path)

    assert loaded.id == mission.id
    assert loaded.directive == mission.directive
    assert loaded.capabilities.git_push is False
    assert loaded.capabilities.network == "brokered"


def test_empty_directive_is_rejected(tmp_path: Path) -> None:
    mission = Mission.draft("   ", str(tmp_path), "human:test")
    assert "directive must not be empty" in mission.validate()
