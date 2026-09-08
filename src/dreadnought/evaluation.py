from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from .order import Order
from .protocol import Perspective, Predicate, ProtocolRecord, RecordKind, VerdictStatus
from .verify import VerifierRegistry, default_registry


@dataclass(frozen=True)
class EvaluationSummary:
    verdicts: tuple[ProtocolRecord, ...]
    accepted: bool
    status: VerdictStatus


def _resolve_path(workspace: Path, raw: str) -> str:
    path = Path(raw)
    if not path.is_absolute():
        path = workspace / path
    return str(path.resolve())


def _claim_verifier(record: ProtocolRecord, workspace: Path) -> tuple[str | None, dict[str, object]]:
    data = record.data
    verifier = data.get("verifier")
    payload = data.get("payload")
    if verifier is not None:
        if not isinstance(verifier, str) or not isinstance(payload, dict):
            return None, {}
        normalized = dict(payload)
        if isinstance(normalized.get("path"), str):
            normalized["path"] = _resolve_path(workspace, str(normalized["path"]))
        if verifier == "process.command" and "cwd" not in normalized:
            normalized["cwd"] = str(workspace)
        return verifier, normalized

    try:
        predicate = Predicate(data.get("predicate"))
    except (TypeError, ValueError):
        return None, {}
    if predicate in {Predicate.EXISTS, Predicate.ABSENT} and record.subject_ref:
        return "filesystem.path", {
            "path": _resolve_path(workspace, record.subject_ref),
            "predicate": predicate.value,
        }
    return None, {}


def _evidence_refs(claim: ProtocolRecord, observation_id: str, status: VerdictStatus) -> list[str]:
    if status in {
        VerdictStatus.UNVERIFIABLE,
        VerdictStatus.NOT_YET_VERIFIED,
        VerdictStatus.MALFORMED,
    }:
        return []
    return [claim.id, observation_id]


def _claim_verdict(
    record: ProtocolRecord,
    *,
    workspace: Path,
    observation_id: str,
    registry: VerifierRegistry,
) -> ProtocolRecord:
    verifier, payload = _claim_verifier(record, workspace)
    if verifier is None:
        status = VerdictStatus.NOT_YET_VERIFIED
        observed = None
        evidence = None
        reason = "claim did not provide a supported verifier payload"
    else:
        result = registry.verify(verifier, payload)
        status = result.status
        observed = result.observed
        evidence = result.evidence
        reason = result.reason
    return ProtocolRecord.create(
        kind=RecordKind.VERDICT,
        perspective=Perspective.EVALUATION,
        actor_id="dreadnought:evaluator",
        order_ref=record.order_ref,
        subject_ref=record.id,
        data={
            "status": status.value,
            "claim_subject_ref": record.subject_ref,
            "verifier": verifier,
            "observed": observed,
            "evidence": evidence,
            "reason": reason,
        },
        evidence_refs=_evidence_refs(record, observation_id, status),
    )


def _acceptance_index(order: Order, reference: object) -> int | None:
    if isinstance(reference, int):
        return reference if 0 <= reference < len(order.acceptance) else None
    if isinstance(reference, str):
        if reference.isdigit():
            idx = int(reference)
            return idx if 0 <= idx < len(order.acceptance) else None
        try:
            return order.acceptance.index(reference)
        except ValueError:
            return None
    return None


def _rollup_status(statuses: list[VerdictStatus]) -> VerdictStatus:
    if not statuses:
        return VerdictStatus.NOT_YET_VERIFIED
    if any(status is VerdictStatus.CONTRADICTED for status in statuses):
        return VerdictStatus.CONTRADICTED
    if any(status is VerdictStatus.MALFORMED for status in statuses):
        return VerdictStatus.MALFORMED
    if any(status is VerdictStatus.UNVERIFIABLE for status in statuses):
        return VerdictStatus.UNVERIFIABLE
    if any(status is VerdictStatus.NOT_YET_VERIFIED for status in statuses):
        return VerdictStatus.NOT_YET_VERIFIED
    if any(status is VerdictStatus.PARTIALLY_SUPPORTED for status in statuses):
        return VerdictStatus.PARTIALLY_SUPPORTED
    return VerdictStatus.SUPPORTED


def evaluate_order(
    order: Order,
    records: Iterable[ProtocolRecord],
    *,
    workspace: Path,
    observation_id: str,
    process_exit_code: int,
    registry: VerifierRegistry | None = None,
) -> EvaluationSummary:
    registry = registry or default_registry()
    claims = [record for record in records if record.kind is RecordKind.CLAIM]
    claim_verdicts = [
        _claim_verdict(
            claim,
            workspace=workspace,
            observation_id=observation_id,
            registry=registry,
        )
        for claim in claims
    ]
    verdict_by_claim = {claim.id: verdict for claim, verdict in zip(claims, claim_verdicts)}

    acceptance_verdicts: list[ProtocolRecord] = []
    acceptance_statuses: list[VerdictStatus] = []
    for index, criterion in enumerate(order.acceptance):
        linked_claims = [
            claim
            for claim in claims
            if _acceptance_index(order, claim.data.get("acceptance_ref")) == index
        ]
        statuses = [
            VerdictStatus(verdict_by_claim[claim.id].data["status"])
            for claim in linked_claims
        ]
        status = _rollup_status(statuses)
        acceptance_statuses.append(status)
        refs = [claim.id for claim in linked_claims]
        evidence_refs = [] if status in {
            VerdictStatus.UNVERIFIABLE,
            VerdictStatus.NOT_YET_VERIFIED,
            VerdictStatus.MALFORMED,
        } else [*refs, observation_id]
        acceptance_verdicts.append(
            ProtocolRecord.create(
                kind=RecordKind.VERDICT,
                perspective=Perspective.EVALUATION,
                actor_id="dreadnought:evaluator",
                order_ref=order.id,
                subject_ref=f"acceptance:{order.id}:{index}",
                data={
                    "status": status.value,
                    "criterion": criterion,
                    "claim_refs": refs,
                },
                evidence_refs=evidence_refs,
            )
        )

    if process_exit_code != 0:
        final_status = VerdictStatus.CONTRADICTED
    elif not order.acceptance:
        final_status = VerdictStatus.SUPPORTED
    else:
        final_status = _rollup_status(acceptance_statuses)

    final_evidence = [] if final_status in {
        VerdictStatus.UNVERIFIABLE,
        VerdictStatus.NOT_YET_VERIFIED,
        VerdictStatus.MALFORMED,
    } else [observation_id, *(verdict.id for verdict in acceptance_verdicts)]
    order_verdict = ProtocolRecord.create(
        kind=RecordKind.VERDICT,
        perspective=Perspective.EVALUATION,
        actor_id="dreadnought:evaluator",
        order_ref=order.id,
        subject_ref=order.id,
        data={
            "status": final_status.value,
            "process_exit_code": process_exit_code,
            "acceptance_count": len(order.acceptance),
            "acceptance_statuses": [status.value for status in acceptance_statuses],
        },
        evidence_refs=final_evidence,
    )

    verdicts = tuple([*claim_verdicts, *acceptance_verdicts, order_verdict])
    return EvaluationSummary(
        verdicts=verdicts,
        accepted=final_status is VerdictStatus.SUPPORTED,
        status=final_status,
    )
