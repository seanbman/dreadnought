from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any
from uuid import uuid4

from .grapher import GrapherControlPlane
from .protocol import Perspective, ProtocolRecord, RecordKind


@dataclass(frozen=True)
class TokenUsage:
    id: str
    recorded_at: str
    agent_id: str
    agent_role: str
    project_id: str
    task_id: str | None
    input_tokens: int
    output_tokens: int
    cached_tokens: int = 0
    reasoning_tokens: int = 0
    provider: str | None = None
    model: str | None = None
    source: str = "reported"

    @property
    def total_tokens(self) -> int:
        return self.input_tokens + self.output_tokens

    @classmethod
    def create(cls, *, agent_id: str, agent_role: str, project_id: str,
               task_id: str | None, input_tokens: int, output_tokens: int,
               cached_tokens: int = 0, reasoning_tokens: int = 0,
               provider: str | None = None, model: str | None = None,
               source: str = "reported") -> "TokenUsage":
        values = [input_tokens, output_tokens, cached_tokens, reasoning_tokens]
        if any(value < 0 for value in values):
            raise ValueError("token counts must be non-negative")
        if agent_role not in {"primary", "minion"}:
            raise ValueError("agent role must be primary or minion")
        return cls(
            id=f"usage-{uuid4().hex}",
            recorded_at=datetime.now(timezone.utc).isoformat(),
            agent_id=agent_id,
            agent_role=agent_role,
            project_id=project_id,
            task_id=task_id,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cached_tokens=cached_tokens,
            reasoning_tokens=reasoning_tokens,
            provider=provider,
            model=model,
            source=source,
        )

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["total_tokens"] = self.total_tokens
        return data


class TokenUsageLedger:
    """Append-only usage ledger plus live unmetered-session coverage."""

    def __init__(self, workspace: Path | str):
        self.workspace = Path(workspace).resolve()
        self.path = self.workspace / ".dreadnought" / "token-usage.jsonl"
        self.sessions_path = self.workspace / ".dreadnought" / "agent-sessions.jsonl"
        self.active_path = self.workspace / ".dreadnought" / "active-agent-sessions.json"

    def record(self, usage: TokenUsage, *, project_to_grapher: bool = True) -> TokenUsage:
        payload = usage.to_dict()
        if project_to_grapher:
            record = ProtocolRecord.create(
                kind=RecordKind.NOTE,
                perspective=Perspective.OBSERVER,
                actor_id="dreadnought:usage-meter",
                subject_ref=usage.task_id or f"project:{usage.project_id}",
                data={"audience": "human", "text": "token_usage " + json.dumps(payload, sort_keys=True)},
            )
            GrapherControlPlane(self.workspace).write_record(record)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(payload, sort_keys=True) + "\n")
        return usage

    def _read_active(self) -> dict[str, dict[str, Any]]:
        if not self.active_path.is_file():
            return {}
        try:
            data = json.loads(self.active_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return {}
        return data if isinstance(data, dict) else {}

    def _write_active(self, rows: dict[str, dict[str, Any]]) -> None:
        self.active_path.parent.mkdir(parents=True, exist_ok=True)
        self.active_path.write_text(json.dumps(rows, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    def mark_active_session(self, *, agent_id: str, agent_role: str, project_id: str,
                            task_id: str | None = None, source: str = "native_interactive_chat") -> str:
        if agent_role not in {"primary", "minion"}:
            raise ValueError("agent role must be primary or minion")
        session_id = f"session-{uuid4().hex}"
        rows = self._read_active()
        rows[session_id] = {
            "id": session_id,
            "recorded_at": datetime.now(timezone.utc).isoformat(),
            "agent_id": agent_id,
            "agent_role": agent_role,
            "project_id": project_id,
            "task_id": task_id,
            "metered": False,
            "state": "active",
            "source": source,
        }
        self._write_active(rows)
        return session_id

    def clear_active_session(self, session_id: str) -> None:
        rows = self._read_active()
        if rows.pop(session_id, None) is not None:
            self._write_active(rows)

    def record_unmetered_session(self, *, agent_id: str, agent_role: str, project_id: str,
                                 task_id: str | None = None, exit_code: int | None = None,
                                 source: str = "native_interactive_chat") -> dict[str, Any]:
        if agent_role not in {"primary", "minion"}:
            raise ValueError("agent role must be primary or minion")
        payload = {
            "id": f"session-{uuid4().hex}",
            "recorded_at": datetime.now(timezone.utc).isoformat(),
            "agent_id": agent_id,
            "agent_role": agent_role,
            "project_id": project_id,
            "task_id": task_id,
            "metered": False,
            "exit_code": exit_code,
            "source": source,
        }
        self.sessions_path.parent.mkdir(parents=True, exist_ok=True)
        with self.sessions_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(payload, sort_keys=True) + "\n")
        return payload

    def entries(self) -> list[dict[str, Any]]:
        if not self.path.is_file():
            return []
        return [json.loads(line) for line in self.path.read_text(encoding="utf-8").splitlines() if line.strip()]

    def sessions(self) -> list[dict[str, Any]]:
        if not self.sessions_path.is_file():
            return []
        return [json.loads(line) for line in self.sessions_path.read_text(encoding="utf-8").splitlines() if line.strip()]

    def active_sessions(self) -> list[dict[str, Any]]:
        return list(self._read_active().values())

    def stats(self, *, project_id: str | None = None, task_id: str | None = None,
              agent_role: str | None = None) -> dict[str, Any]:
        rows = self.entries()
        sessions = self.sessions()
        active = self.active_sessions()
        if project_id is not None:
            rows = [row for row in rows if row.get("project_id") == project_id]
            sessions = [row for row in sessions if row.get("project_id") == project_id]
            active = [row for row in active if row.get("project_id") == project_id]
        if task_id is not None:
            rows = [row for row in rows if row.get("task_id") == task_id]
            sessions = [row for row in sessions if row.get("task_id") == task_id]
            active = [row for row in active if row.get("task_id") == task_id]
        if agent_role is not None:
            rows = [row for row in rows if row.get("agent_role") == agent_role]
            sessions = [row for row in sessions if row.get("agent_role") == agent_role]
            active = [row for row in active if row.get("agent_role") == agent_role]
        by_agent: dict[str, int] = {}
        by_project: dict[str, int] = {}
        by_task: dict[str, int] = {}
        by_role = {"primary": 0, "minion": 0}
        for row in rows:
            total = int(row.get("total_tokens") or (row.get("input_tokens", 0) + row.get("output_tokens", 0)))
            by_agent[row["agent_id"]] = by_agent.get(row["agent_id"], 0) + total
            by_project[row["project_id"]] = by_project.get(row["project_id"], 0) + total
            if row.get("task_id"):
                by_task[row["task_id"]] = by_task.get(row["task_id"], 0) + total
            role = row.get("agent_role")
            if role in by_role:
                by_role[role] += total
        unmetered_by_role = {"primary": 0, "minion": 0}
        for session in [*sessions, *active]:
            role = session.get("agent_role")
            if role in unmetered_by_role:
                unmetered_by_role[role] += 1
        unmetered_count = len(sessions) + len(active)
        return {
            "records": len(rows),
            "total_tokens": sum(by_agent.values()),
            "by_role": by_role,
            "by_agent": by_agent,
            "by_project": by_project,
            "by_task": by_task,
            "metering": {
                "complete": unmetered_count == 0,
                "unmetered_sessions": unmetered_count,
                "active_unmetered_sessions": len(active),
                "active_sessions": active,
                "unmetered_by_role": unmetered_by_role,
                "note": (
                    "Token totals include provider-reported usage only. Active or native sessions without provider counters are reported explicitly rather than as zero-token usage."
                    if unmetered_count else
                    "All recorded sessions in this view have provider-reported token usage."
                ),
            },
        }
