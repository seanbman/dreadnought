from __future__ import annotations

from pathlib import Path
import json

from .protocol import Perspective, ProtocolRecord, RecordKind


AGENT_ALLOWED_KINDS = {
    RecordKind.CLAIM,
    RecordKind.ACTION,
    RecordKind.ARTIFACT,
    RecordKind.REQUIREMENT,
    RecordKind.RISK,
    RecordKind.NOTE,
}


class AgentResultChannel:
    """Read typed agent-authored protocol records from external scratch.

    The channel is deliberately one-way from the agent's writable scratch into
    Dreadnought. Observer and evaluation records are rejected regardless of
    their contents so an agent cannot self-promote testimony into authority.
    """

    def read(self, path: Path) -> list[ProtocolRecord]:
        if not path.exists():
            return []
        records: list[ProtocolRecord] = []
        for line_number, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
            if not raw.strip():
                continue
            try:
                payload = json.loads(raw)
                record = ProtocolRecord.from_dict(payload)
            except (json.JSONDecodeError, KeyError, TypeError, ValueError) as exc:
                raise ValueError(f"invalid agent result at line {line_number}: {exc}") from exc
            errors = record.validate()
            if errors:
                raise ValueError(f"invalid agent result at line {line_number}: {'; '.join(errors)}")
            if record.perspective is not Perspective.AGENT:
                raise ValueError(f"agent result line {line_number} must use agent perspective")
            if record.kind not in AGENT_ALLOWED_KINDS:
                raise ValueError(f"agent result line {line_number} uses reserved kind {record.kind.value}")
            records.append(record)
        return records
