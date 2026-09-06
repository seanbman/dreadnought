from __future__ import annotations

from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any
from uuid import uuid4

from .doctrine import AGENCY_LEVELS


@dataclass
class Order:
    id: str
    doctrine_ref: str
    campaign_ref: str
    operation_ref: str
    project_arm: str
    objective: str
    created_at: str
    source_refs: list[str] = field(default_factory=list)
    relevant_requirements: list[str] = field(default_factory=list)
    include_scope: list[str] = field(default_factory=list)
    exclude_scope: list[str] = field(default_factory=list)
    acceptance: list[str] = field(default_factory=list)
    requested_capabilities: list[str] = field(default_factory=list)
    creative_authority: dict[str, str] = field(default_factory=dict)
    human_notes: list[str] = field(default_factory=list)

    @classmethod
    def draft(
        cls,
        doctrine_ref: str,
        campaign_ref: str,
        operation_ref: str,
        objective: str,
        project_arm: str = "project-arm-1",
    ) -> "Order":
        return cls(
            id=f"order-{uuid4().hex[:12]}",
            doctrine_ref=doctrine_ref,
            campaign_ref=campaign_ref,
            operation_ref=operation_ref,
            project_arm=project_arm,
            objective=objective,
            created_at=datetime.now(timezone.utc).isoformat(),
        )

    def validate(self) -> list[str]:
        errors: list[str] = []
        required = {
            "doctrine_ref": self.doctrine_ref,
            "campaign_ref": self.campaign_ref,
            "operation_ref": self.operation_ref,
            "project_arm": self.project_arm,
            "objective": self.objective,
        }
        for name, value in required.items():
            if not value.strip():
                errors.append(f"{name} must not be empty")
        for domain, level in self.creative_authority.items():
            if level not in AGENCY_LEVELS:
                errors.append(f"invalid creative authority level for {domain}: {level}")
        return errors

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "Order":
        return cls(**payload)

    @classmethod
    def read(cls, path: Path) -> "Order":
        return cls.from_dict(json.loads(path.read_text()))

    def write(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(self.to_dict(), indent=2) + "\n")
