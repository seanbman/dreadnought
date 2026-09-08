from pathlib import Path

from dreadnought.mission import CapabilitySet, Mission, MissionStatus


def test_draft_round_trip(tmp_path: Path) -> None:
    mission = Mission.draft(
        directive="Inspect the workspace and propose a patch.",
        workspace=str(tmp_path),
        actor_id="human:test",
    )
    assert mission.status is MissionStatus.DRAFT
    assert mission.validate() == []
    assert mission.capabilities.max_minions is None

    path = tmp_path / "mission.json"
    mission.write(path)
    loaded = Mission.read(path)

    assert loaded.id == mission.id
    assert loaded.directive == mission.directive
    assert loaded.capabilities.git_push is False
    assert loaded.capabilities.network == "brokered"
    assert loaded.capabilities.max_minions is None


def test_zero_minions_is_an_explicit_valid_prohibition(tmp_path: Path) -> None:
    mission = Mission.draft("Do the work without delegation.", str(tmp_path), "human:test")
    mission.capabilities = CapabilitySet(max_minions=0)
    assert mission.validate() == []


def test_negative_minion_limit_is_rejected(tmp_path: Path) -> None:
    mission = Mission.draft("Delegate as needed.", str(tmp_path), "human:test")
    mission.capabilities = CapabilitySet(max_minions=-1)
    assert "max_minions must be >= 0 when supplied" in mission.validate()


def test_empty_directive_is_rejected(tmp_path: Path) -> None:
    mission = Mission.draft("   ", str(tmp_path), "human:test")
    assert "directive must not be empty" in mission.validate()
