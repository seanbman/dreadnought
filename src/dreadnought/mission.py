from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import StrEnum
from pathlib import Path
from typing import Any
import json
import uuid


SCHEMA_VERSION = "0.1"


class MissionStatus(StrEnum):
    DRAFT = "draft"
    NORMALIZED = "normalized"
    VALIDATED = "validated"
    READY = "ready"
    RUNNING = "running"
    BLOCKED = "blocked"
    COMPLETED = "completed"
    ACCEPTED = "accepted"
    CLOSED = "closed"
    FAILED = "failed"


class SourceType(StrEnum):
    WORKSPACE = "workspace"
    GITHUB = "github"
    GOOGLE_DRIVE = "google_drive"
    FILE = "file"
    URL = "url"
    OTHER = "other"


class AccessMode(StrEnum):
    READ = "read"
    PROPOSE_WRITE = "propose_write"
    WRITE = "write"


@dataclass(frozen=True)
class Source:
    id: str
    type: SourceType
    locator: str
    access: AccessMode = AccessMode.READ


@dataclass(frozen=True)
class CapabilitySet:
    canonical_workspace: AccessMode = AccessMode.READ
    scratch_write: bool = True
    git_inspect: bool = True
    git_propose_commit: bool = True
    git_push: bool = False
    network: str = "brokered"
    shell: str = "restricted"
    max_minions: int = 0


@dataclass
class Mission:
    id: str
    created_at: str
    directive: str
    workspace: str
    actor_id: str
    status: MissionStatus = MissionStatus.DRAFT
    objective: str | None = None
    sources: list[Source] = field(default_factory=list)
    capabilities: CapabilitySet = field(default_factory=CapabilitySet)
    requirements: list[str] = field(default_factory=list)
    human_notes: list[str] = field(default_factory=list)
    schema_version: str = SCHEMA_VERSION

    @classmethod
    def draft(cls, directive: str, workspace: str, actor_id: str) -> "Mission":
        return cls(
            id=f"mission-{uuid.uuid4().hex[:12]}",
            created_at=datetime.now(timezone.utc).isoformat(),
            directive=directive.strip(),
            workspace=workspace,
            actor_id=actor_id,
        )

    def validate(self) -> list[str]:
        errors: list[str] = []
        if not self.directive.strip():
            errors.append("directive must not be empty")
        if not self.workspace.strip():
            errors.append("workspace must not be empty")
        if not self.actor_id.strip():
            errors.append("actor_id must not be empty")
        if self.capabilities.max_minions < 0:
            errors.append("max_minions must be >= 0")
        if self.capabilities.network not in {"none", "brokered", "unrestricted"}:
            errors.append("network must be one of: none, brokered, unrestricted")
        if self.capabilities.shell not in {"none", "restricted", "unrestricted"}:
            errors.append("shell must be one of: none, restricted, unrestricted")
        source_ids = [source.id for source in self.sources]
        if len(source_ids) != len(set(source_ids)):
            errors.append("source ids must be unique")
        return errors

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    def write(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(self.to_dict(), indent=2) + "\n", encoding="utf-8")

    @classmethod
    def read(cls, path: Path) -> "Mission":
        raw = json.loads(path.read_text(encoding="utf-8"))
        raw["status"] = MissionStatus(raw["status"])
        raw["sources"] = [
            Source(
                id=item["id"],
                type=SourceType(item["type"]),
                locator=item["locator"],
                access=AccessMode(item.get("access", "read")),
            )
            for item in raw.get("sources", [])
        ]
        caps = raw.get("capabilities", {})
        if "canonical_workspace" in caps:
            caps["canonical_workspace"] = AccessMode(caps["canonical_workspace"])
        raw["capabilities"] = CapabilitySet(**caps)
        return cls(**raw)
