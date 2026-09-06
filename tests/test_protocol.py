from dreadnought.protocol import (
    ObservationType,
    Perspective,
    Predicate,
    ProtocolRecord,
    RecordKind,
    RequirementStatus,
    VerdictStatus,
)


def test_agent_claim_round_trip(tmp_path):
    record = ProtocolRecord.claim(
        actor_id="agent:arm-1",
        subject_ref="test-suite:project",
        predicate=Predicate.SUCCEEDS,
        order_ref="order-1",
    )
    assert record.validate() == []
    path = tmp_path / "claim.json"
    record.write(path)
    loaded = ProtocolRecord.read(path)
    assert loaded.kind is RecordKind.CLAIM
    assert loaded.data["predicate"] == "succeeds"


def test_agent_cannot_author_observation():
    record = ProtocolRecord.create(
        kind=RecordKind.OBSERVATION,
        perspective=Perspective.AGENT,
        actor_id="agent:a",
        subject_ref="command:1",
        data={"observation_type": ObservationType.COMMAND.value, "result": {"exit_code": 0}},
    )
    assert "observation records are reserved to observer perspective" in record.validate()


def test_observer_observation_is_valid():
    record = ProtocolRecord.create(
        kind=RecordKind.OBSERVATION,
        perspective=Perspective.OBSERVER,
        actor_id="dreadnought:observer",
        data={"observation_type": "test", "result": {"exit_code": 1}},
    )
    assert record.validate() == []


def test_only_evaluation_can_verify_requirement():
    record = ProtocolRecord.create(
        kind=RecordKind.REQUIREMENT,
        perspective=Perspective.AGENT,
        actor_id="agent:a",
        subject_ref="requirement:R1",
        data={"status": RequirementStatus.VERIFIED.value},
    )
    assert "only evaluation perspective may mark a requirement verified" in record.validate()


def test_supported_verdict_requires_evidence():
    record = ProtocolRecord.create(
        kind=RecordKind.VERDICT,
        perspective=Perspective.EVALUATION,
        actor_id="dreadnought:evaluator",
        subject_ref="claim:1",
        data={"status": VerdictStatus.SUPPORTED.value},
    )
    assert "evidence-bearing verdicts require evidence_refs" in record.validate()


def test_unverifiable_verdict_may_have_no_evidence():
    record = ProtocolRecord.create(
        kind=RecordKind.VERDICT,
        perspective=Perspective.EVALUATION,
        actor_id="dreadnought:evaluator",
        subject_ref="claim:1",
        data={"status": VerdictStatus.UNVERIFIABLE.value},
    )
    assert record.validate() == []


def test_note_is_explicitly_human_facing():
    record = ProtocolRecord.note(actor_id="agent:a", text="Please review layout judgment.")
    assert record.validate() == []
    assert record.data["audience"] == "human"
