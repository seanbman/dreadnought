from pathlib import Path

from dreadnought.evaluation import evaluate_order
from dreadnought.order import Order
from dreadnought.protocol import ArtifactType, Perspective, ProtocolRecord, RecordKind
from dreadnought.training import TrainingCorpus


def make_order() -> Order:
    order = Order.draft(
        doctrine_ref="doctrine-1",
        campaign_ref="campaign-1",
        operation_ref="operation-1",
        objective="Implement a bounded Koffer change",
        project_arm="koffer-library",
        project_id="koffer",
    )
    return order


def test_training_episode_is_normalized_and_redacts_absolute_artifact_paths(tmp_path: Path) -> None:
    workspace = tmp_path / "control"
    project = tmp_path / "koffer"
    workspace.mkdir()
    project.mkdir()
    order = make_order()
    scratch = tmp_path / "scratch"
    artifact_path = scratch / "src" / "koffer" / "scanner.py"
    artifact_path.parent.mkdir(parents=True)
    artifact_path.write_text("print('scan')\n")
    instructions = workspace / ".dreadnought" / "INSTRUCTIONS.md"
    instructions.parent.mkdir(parents=True)
    instructions.write_text("Koffer bounded work\n")
    artifact = ProtocolRecord.create(
        kind=RecordKind.ARTIFACT,
        perspective=Perspective.AGENT,
        actor_id="codex",
        order_ref=order.id,
        data={"artifact_type": ArtifactType.FILE.value, "ref": str(artifact_path)},
    )
    evaluation = evaluate_order(
        order,
        [artifact],
        workspace=project,
        observation_id="observation-1",
        process_exit_code=0,
    )

    episode = TrainingCorpus(workspace).record_dispatch(
        order=order,
        project_root=project,
        scratch_root=scratch,
        adapter_id="codex",
        network_policy="host",
        exit_code=0,
        duration_ms=25,
        observation_id="observation-1",
        agent_records=[artifact],
        evaluation=evaluation,
        usage={"input_tokens": 10, "output_tokens": 5, "provider": "openai-codex-cli", "model": "fixture"},
    )

    assert episode["evaluation"]["accepted"] is True
    assert (workspace / ".dreadnought" / "training" / ".gitignore").read_text() == "*\n!.gitignore\n"
    assert episode["project"]["repository"] is None
    assert episode["project"]["branch"] is None
    assert episode["dataset"]["eligible"] is True
    assert episode["dataset"]["redacted"] is True
    assert episode["artifacts"][0]["scope"] == "scratch"
    assert episode["artifacts"][0]["ref"] == "src/koffer/scanner.py"
    assert episode["artifacts"][0]["hash_status"] == "hashed"
    assert episode["artifacts"][0]["sha256"]
    assert episode["agent_testimony"][0]["data"]["ref"] == "scratch:src/koffer/scanner.py"
    assert episode["dreadnought"]["instructions_sha256"]
    assert episode["lineage"] == {"parent_episode_id": None, "retry_index": 0}
    assert episode["execution"]["failure_category"] is None
    assert str(tmp_path) not in TrainingCorpus(workspace).episodes_path.read_text(encoding="utf-8")


def test_failed_episode_is_retained_but_not_training_eligible(tmp_path: Path) -> None:
    workspace = tmp_path / "control"
    project = tmp_path / "koffer"
    workspace.mkdir()
    project.mkdir()
    order = make_order()
    evaluation = evaluate_order(
        order,
        [],
        workspace=project,
        observation_id="observation-2",
        process_exit_code=2,
    )

    episode = TrainingCorpus(workspace).record_dispatch(
        order=order,
        project_root=project,
        adapter_id="codex",
        network_policy="none",
        exit_code=2,
        duration_ms=5,
        observation_id="observation-2",
        agent_records=[],
        evaluation=evaluation,
    )

    assert episode["evaluation"]["accepted"] is False
    assert episode["dataset"]["eligible"] is False
    assert episode["execution"]["failure_category"] == "process_exit_nonzero"
    assert "order_not_accepted" in episode["dataset"]["exclusion_reasons"]


def test_feedback_is_append_only_and_joined_on_export(tmp_path: Path) -> None:
    workspace = tmp_path / "control"
    project = tmp_path / "koffer"
    workspace.mkdir()
    project.mkdir()
    order = make_order()
    evaluation = evaluate_order(
        order,
        [],
        workspace=project,
        observation_id="observation-3",
        process_exit_code=0,
    )
    corpus = TrainingCorpus(workspace)
    episode = corpus.record_dispatch(
        order=order,
        project_root=project,
        adapter_id="fixture",
        network_policy="none",
        exit_code=0,
        duration_ms=1,
        observation_id="observation-3",
        agent_records=[],
        evaluation=evaluation,
    )
    feedback = corpus.record_feedback(
        episode["episode_id"],
        rating="revise",
        comment="Keep scanning off the UI thread.",
    )
    out = tmp_path / "export.jsonl"
    report = corpus.export(out, mode="all", eval_percent=20, split_seed="koffer-v1")
    row = __import__("json").loads(out.read_text(encoding="utf-8").strip())

    assert report["records"] == 1
    assert report["train_records"] + report["eval_records"] == 1
    assert row["dataset"]["split"] in {"train", "eval"}
    assert row["feedback_refs"] == [feedback["feedback_id"]]
    assert row["human_feedback"][0]["feedback_id"] == feedback["feedback_id"]
    assert row["human_feedback"][0]["comment"] == "Keep scanning off the UI thread."
