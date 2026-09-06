from __future__ import annotations

from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any
from uuid import uuid4


@dataclass
class Operation:
    id: str
    title: str
    objective: str
    dependencies: list[str] = field(default_factory=list)
    include_scope: list[str] = field(default_factory=list)
    exclude_scope: list[str] = field(default_factory=list)
    required_outcomes: list[str] = field(default_factory=list)


@dataclass
class CampaignPlan:
    id: str
    doctrine_ref: str
    created_at: str
    task_group: str
    operations: list[Operation] = field(default_factory=list)

    @classmethod
    def draft(cls, doctrine_ref: str, task_group: str = "task-group-1") -> "CampaignPlan":
        return cls(
            id=f"campaign-{uuid4().hex[:12]}",
            doctrine_ref=doctrine_ref,
            created_at=datetime.now(timezone.utc).isoformat(),
            task_group=task_group,
        )

    def validate(self) -> list[str]:
        errors: list[str] = []
        if not self.doctrine_ref.strip():
            errors.append("doctrine_ref must not be empty")
        if not self.task_group.strip():
            errors.append("task_group must not be empty")
        ids = [op.id for op in self.operations]
        if len(ids) != len(set(ids)):
            errors.append("operation ids must be unique")
        known = set(ids)
        for op in self.operations:
            for dep in op.dependencies:
                if dep not in known:
                    errors.append(f"operation {op.id} depends on unknown operation {dep}")
        return errors

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "CampaignPlan":
        data = dict(payload)
        operations = [Operation(**item) for item in data.pop("operations", [])]
        return cls(operations=operations, **data)

    @classmethod
    def read(cls, path: Path) -> "CampaignPlan":
        return cls.from_dict(json.loads(path.read_text()))

    def write(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(self.to_dict(), indent=2) + "\n")
