from __future__ import annotations

from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from enum import Enum
import json
from pathlib import Path
from typing import Any
from uuid import uuid4


SCHEMA_VERSION = 1


class RecordKind(str, Enum):
    CLAIM = "claim"
    OBSERVATION = "observation"
    ACTION = "action"
    ARTIFACT = "artifact"
    REQUIREMENT = "requirement"
    RISK = "risk"
    NOTE = "note"
    VERDICT = "verdict"


class Perspective(str, Enum):
    HUMAN_SOURCE = "human_source"
    AGENT = "agent"
    OBSERVER = "observer"
    EVALUATION = "evaluation"


class Predicate(str, Enum):
    EXISTS = "exists"
    ABSENT = "absent"
    EQUALS = "equals"
    SUCCEEDS = "succeeds"
    FAILS = "fails"
    COMPLETE = "complete"
    UNCHANGED = "unchanged"


class ObservationType(str, Enum):
    COMMAND = "command"
    FILESYSTEM = "filesystem"
    GIT = "git"
    TEST = "test"
    BUILD = "build"
    HTTP = "http"
    PROCESS = "process"


class ActionType(str, Enum):
    PROPOSE = "propose"
    REQUEST = "request"
    CANCEL = "cancel"


class ArtifactType(str, Enum):
    FILE = "file"
    PATCH = "patch"
    COMMIT = "commit"
    PULL_REQUEST = "pull_request"
    REPORT = "report"
    DESIGN = "design"
    SCHEMA = "schema"


class RequirementStatus(str, Enum):
    PROPOSED = "proposed"
    ACCEPTED = "accepted"
    IMPLEMENTED = "implemented"
    BLOCKED = "blocked"
    REJECTED = "rejected"
    VERIFIED = "verified"


class RiskCategory(str, Enum):
    REGRESSION = "regression"
    SECURITY = "security"
    DATA_LOSS = "data_loss"
    COMPATIBILITY = "compatibility"
    PERFORMANCE = "performance"
    USABILITY = "usability"
    DEPENDENCY = "dependency"


class Severity(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class VerdictStatus(str, Enum):
    SUPPORTED = "supported"
    CONTRADICTED = "contradicted"
    PARTIALLY_SUPPORTED = "partially_supported"
    UNVERIFIABLE = "unverifiable"
    NOT_YET_VERIFIED = "not_yet_verified"
    MALFORMED = "malformed"


@dataclass
class ProtocolRecord:
    id: str
    kind: RecordKind
    perspective: Perspective
    actor_id: str
    created_at: str
    schema_version: int = SCHEMA_VERSION
    mission_ref: str | None = None
    doctrine_ref: str | None = None
    order_ref: str | None = None
    subject_ref: str | None = None
    data: dict[str, Any] = field(default_factory=dict)
    evidence_refs: list[str] = field(default_factory=list)

    @classmethod
    def create(
        cls,
        *,
        kind: RecordKind,
        perspective: Perspective,
        actor_id: str,
        data: dict[str, Any],
        mission_ref: str | None = None,
        doctrine_ref: str | None = None,
        order_ref: str | None = None,
        subject_ref: str | None = None,
        evidence_refs: list[str] | None = None,
    ) -> "ProtocolRecord":
        return cls(
            id=f"record-{uuid4().hex[:12]}",
            kind=kind,
            perspective=perspective,
            actor_id=actor_id,
            created_at=datetime.now(timezone.utc).isoformat(),
            mission_ref=mission_ref,
            doctrine_ref=doctrine_ref,
            order_ref=order_ref,
            subject_ref=subject_ref,
            data=data,
            evidence_refs=list(evidence_refs or []),
        )

    @classmethod
    def claim(
        cls,
        *,
        actor_id: str,
        subject_ref: str,
        predicate: Predicate,
        expected: Any = None,
        order_ref: str | None = None,
        evidence_refs: list[str] | None = None,
    ) -> "ProtocolRecord":
        data: dict[str, Any] = {"predicate": predicate.value}
        if expected is not None:
            data["expected"] = expected
        return cls.create(
            kind=RecordKind.CLAIM,
            perspective=Perspective.AGENT,
            actor_id=actor_id,
            subject_ref=subject_ref,
            order_ref=order_ref,
            data=data,
            evidence_refs=evidence_refs,
        )

    @classmethod
    def note(cls, *, actor_id: str, text: str, audience: str = "human") -> "ProtocolRecord":
        return cls.create(
            kind=RecordKind.NOTE,
            perspective=Perspective.AGENT,
            actor_id=actor_id,
            data={"audience": audience, "text": text},
        )

    def validate(self) -> list[str]:
        errors: list[str] = []
        if self.schema_version != SCHEMA_VERSION:
            errors.append(f"unsupported schema_version {self.schema_version}")
        if not self.actor_id.strip():
            errors.append("actor_id must not be empty")
        if not isinstance(self.data, dict):
            errors.append("data must be an object")
            return errors

        if self.kind is RecordKind.CLAIM:
            if self.perspective is not Perspective.AGENT:
                errors.append("claim records must use agent perspective")
            if not self.subject_ref:
                errors.append("claim records require subject_ref")
            try:
                Predicate(self.data.get("predicate"))
            except (ValueError, TypeError):
                errors.append("claim records require a recognized predicate")

        elif self.kind is RecordKind.OBSERVATION:
            if self.perspective is not Perspective.OBSERVER:
                errors.append("observation records are reserved to observer perspective")
            try:
                ObservationType(self.data.get("observation_type"))
            except (ValueError, TypeError):
                errors.append("observation records require a recognized observation_type")
            if "result" not in self.data:
                errors.append("observation records require result")

        elif self.kind is RecordKind.ACTION:
            try:
                ActionType(self.data.get("action_type"))
            except (ValueError, TypeError):
                errors.append("action records require a recognized action_type")
            if self.perspective not in {Perspective.AGENT, Perspective.HUMAN_SOURCE}:
                errors.append("action records represent proposed/requested action, not observer execution")

        elif self.kind is RecordKind.ARTIFACT:
            try:
                ArtifactType(self.data.get("artifact_type"))
            except (ValueError, TypeError):
                errors.append("artifact records require a recognized artifact_type")
            if not self.data.get("ref"):
                errors.append("artifact records require ref")

        elif self.kind is RecordKind.REQUIREMENT:
            try:
                status = RequirementStatus(self.data.get("status"))
            except (ValueError, TypeError):
                errors.append("requirement records require a recognized status")
            else:
                if status is RequirementStatus.VERIFIED and self.perspective is not Perspective.EVALUATION:
                    errors.append("only evaluation perspective may mark a requirement verified")

        elif self.kind is RecordKind.RISK:
            try:
                RiskCategory(self.data.get("category"))
            except (ValueError, TypeError):
                errors.append("risk records require a recognized category")
            try:
                Severity(self.data.get("severity"))
            except (ValueError, TypeError):
                errors.append("risk records require a recognized severity")

        elif self.kind is RecordKind.NOTE:
            if not str(self.data.get("text", "")).strip():
                errors.append("note records require non-empty text")
            if self.data.get("audience") != "human":
                errors.append("notes are human-facing and must set audience=human")

        elif self.kind is RecordKind.VERDICT:
            if self.perspective is not Perspective.EVALUATION:
                errors.append("verdict records are reserved to evaluation perspective")
            try:
                VerdictStatus(self.data.get("status"))
            except (ValueError, TypeError):
                errors.append("verdict records require a recognized status")
            if not self.subject_ref:
                errors.append("verdict records require subject_ref")
            if not self.evidence_refs and self.data.get("status") not in {
                VerdictStatus.UNVERIFIABLE.value,
                VerdictStatus.NOT_YET_VERIFIED.value,
                VerdictStatus.MALFORMED.value,
            }:
                errors.append("evidence-bearing verdicts require evidence_refs")

        return errors

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["kind"] = self.kind.value
        payload["perspective"] = self.perspective.value
        return payload

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "ProtocolRecord":
        data = dict(payload)
        data["kind"] = RecordKind(data["kind"])
        data["perspective"] = Perspective(data["perspective"])
        return cls(**data)

    @classmethod
    def read(cls, path: Path) -> "ProtocolRecord":
        return cls.from_dict(json.loads(path.read_text()))

    def write(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(self.to_dict(), indent=2) + "\n")
