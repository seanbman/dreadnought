from pathlib import Path

from dreadnought.evaluation import evaluate_order
from dreadnought.order import Order
from dreadnought.protocol import Predicate, ProtocolRecord, VerdictStatus


def make_order() -> Order:
    order = Order.draft(
        doctrine_ref="doctrine-1",
        campaign_ref="campaign-1",
        operation_ref="operation-1",
        objective="Implement verified change",
    )
    order.acceptance = ["marker exists", "tests pass"]
    return order


def test_acceptance_requires_linked_verified_claims(tmp_path: Path) -> None:
    order = make_order()
    marker = tmp_path / "marker.txt"
    marker.write_text("ok")
    claim = ProtocolRecord.claim(
        actor_id="minion",
        subject_ref="marker.txt",
        predicate=Predicate.EXISTS,
        order_ref=order.id,
    )
    claim.data["acceptance_ref"] = 0

    summary = evaluate_order(
        order,
        [claim],
        workspace=tmp_path,
        observation_id="observation-1",
        process_exit_code=0,
    )

    assert summary.accepted is False
    assert summary.status is VerdictStatus.NOT_YET_VERIFIED
    statuses = [record.data["status"] for record in summary.verdicts]
    assert VerdictStatus.SUPPORTED.value in statuses
    assert VerdictStatus.NOT_YET_VERIFIED.value in statuses


def test_all_acceptance_criteria_verified_accepts_order(tmp_path: Path) -> None:
    order = make_order()
    marker = tmp_path / "marker.txt"
    marker.write_text("ok")

    exists = ProtocolRecord.claim(
        actor_id="minion",
        subject_ref="marker.txt",
        predicate=Predicate.EXISTS,
        order_ref=order.id,
    )
    exists.data["acceptance_ref"] = 0

    command = ProtocolRecord.claim(
        actor_id="minion",
        subject_ref="project tests",
        predicate=Predicate.SUCCEEDS,
        order_ref=order.id,
    )
    command.data.update({
        "acceptance_ref": 1,
        "verifier": "process.command",
        "payload": {"argv": ["python", "-c", "raise SystemExit(0)"], "expected_exit": 0},
    })

    summary = evaluate_order(
        order,
        [exists, command],
        workspace=tmp_path,
        observation_id="observation-1",
        process_exit_code=0,
    )

    assert summary.accepted is True
    assert summary.status is VerdictStatus.SUPPORTED
    assert summary.verdicts[-1].subject_ref == order.id
    assert summary.verdicts[-1].data["status"] == VerdictStatus.SUPPORTED.value


def test_nonzero_minion_exit_contradicts_order_even_if_claims_pass(tmp_path: Path) -> None:
    order = Order.draft(
        doctrine_ref="doctrine-1",
        campaign_ref="campaign-1",
        operation_ref="operation-1",
        objective="Run bounded task",
    )
    summary = evaluate_order(
        order,
        [],
        workspace=tmp_path,
        observation_id="observation-1",
        process_exit_code=2,
    )
    assert summary.accepted is False
    assert summary.status is VerdictStatus.CONTRADICTED
