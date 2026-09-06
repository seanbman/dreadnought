from pathlib import Path
import json

import pytest

from dreadnought.protocol import ObservationType, Perspective, Predicate, ProtocolRecord, RecordKind
from dreadnought.result_channel import AgentResultChannel


def write_jsonl(path: Path, *records: ProtocolRecord) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(record.to_dict()) + "\n" for record in records), encoding="utf-8")


def test_reads_agent_claims(tmp_path: Path) -> None:
    claim = ProtocolRecord.claim(
        actor_id="agent:fixture",
        subject_ref="tests",
        predicate=Predicate.SUCCEEDS,
    )
    path = tmp_path / "result.jsonl"
    write_jsonl(path, claim)
    records = AgentResultChannel().read(path)
    assert [record.id for record in records] == [claim.id]
    assert records[0].perspective is Perspective.AGENT


def test_missing_result_file_is_empty(tmp_path: Path) -> None:
    assert AgentResultChannel().read(tmp_path / "missing.jsonl") == []


def test_rejects_agent_authored_observation(tmp_path: Path) -> None:
    observation = ProtocolRecord.create(
        kind=RecordKind.OBSERVATION,
        perspective=Perspective.OBSERVER,
        actor_id="agent:fixture",
        subject_ref="workspace",
        data={"observation_type": ObservationType.FILESYSTEM.value, "result": {"exists": True}},
    )
    path = tmp_path / "result.jsonl"
    write_jsonl(path, observation)
    with pytest.raises(ValueError, match="agent perspective"):
        AgentResultChannel().read(path)


def test_rejects_malformed_jsonl(tmp_path: Path) -> None:
    path = tmp_path / "result.jsonl"
    path.write_text("{not-json}\n", encoding="utf-8")
    with pytest.raises(ValueError, match="line 1"):
        AgentResultChannel().read(path)
