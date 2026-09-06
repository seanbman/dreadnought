from __future__ import annotations

from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any
from uuid import uuid4


AGENCY_LEVELS = {"prohibited", "approval_required", "low", "medium", "high"}


@dataclass
class Doctrine:
    id: str
    version: int
    created_at: str
    originating_actor: str
    objective: str
    source_refs: list[str] = field(default_factory=list)
    requirements: list[str] = field(default_factory=list)
    constraints: list[str] = field(default_factory=list)
    priorities: list[str] = field(default_factory=list)
    acceptance: list[str] = field(default_factory=list)
    unresolved: list[str] = field(default_factory=list)
    creative_authority: dict[str, str] = field(default_factory=dict)
    human_notes: list[str] = field(default_factory=list)

    @classmethod
    def draft(cls, objective: str, actor_id: str = "human:user") -> "Doctrine":
        return cls(
            id=f"doctrine-{uuid4().hex[:12]}",
            version=1,
            created_at=datetime.now(timezone.utc).isoformat(),
            originating_actor=actor_id,
            objective=objective,
        )

    def validate(self) -> list[str]:
        errors: list[str] = []
        if not self.objective.strip():
            errors.append("objective must not be empty")
        if self.version < 1:
            errors.append("version must be >= 1")
        for domain, level in self.creative_authority.items():
            if not domain.strip():
                errors.append("creative authority domain must not be empty")
            if level not in AGENCY_LEVELS:
                errors.append(f"invalid creative authority level for {domain}: {level}")
        return errors

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "Doctrine":
        return cls(**payload)

    @classmethod
    def read(cls, path: Path) -> "Doctrine":
        return cls.from_dict(json.loads(path.read_text()))

    def write(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(self.to_dict(), indent=2) + "\n")
