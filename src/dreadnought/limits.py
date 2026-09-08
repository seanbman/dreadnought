from __future__ import annotations

from contextlib import contextmanager
from datetime import datetime, timezone
import fcntl
import json
import os
from pathlib import Path
from typing import Iterator
from uuid import uuid4


class MinionSlotManager:
    """Cross-process project-scoped concurrent minion accounting."""

    def __init__(self, workspace: Path | str):
        self.workspace = Path(workspace).resolve()
        self.runtime_dir = self.workspace / ".dreadnought" / "runtime"
        self.lock_path = self.runtime_dir / "minions.lock"
        self.state_path = self.runtime_dir / "minions.json"

    def _load(self) -> dict[str, dict[str, object]]:
        if not self.state_path.is_file():
            return {}
        try:
            data = json.loads(self.state_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return {}
        return data if isinstance(data, dict) else {}

    def _save(self, state: dict[str, dict[str, object]]) -> None:
        self.runtime_dir.mkdir(parents=True, exist_ok=True)
        self.state_path.write_text(json.dumps(state, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    @staticmethod
    def _pid_alive(pid: int) -> bool:
        try:
            os.kill(pid, 0)
        except ProcessLookupError:
            return False
        except PermissionError:
            return True
        return True

    def _prune(self, state: dict[str, dict[str, object]]) -> dict[str, dict[str, object]]:
        return {
            lease_id: item
            for lease_id, item in state.items()
            if self._pid_alive(int(item.get("pid") or 0))
        }

    @contextmanager
    def lease(self, project_id: str, limit: int | None) -> Iterator[str]:
        if limit is not None and limit < 0:
            raise ValueError("max_minions must be >= 0 when supplied")
        self.runtime_dir.mkdir(parents=True, exist_ok=True)
        lease_id = f"minion-{uuid4().hex}"
        with self.lock_path.open("a+", encoding="utf-8") as lock:
            fcntl.flock(lock.fileno(), fcntl.LOCK_EX)
            state = self._prune(self._load())
            active = sum(1 for item in state.values() if item.get("project_id") == project_id)
            if limit is not None and active >= limit:
                raise RuntimeError(f"project {project_id} reached max_minions={limit}")
            state[lease_id] = {
                "project_id": project_id,
                "pid": os.getpid(),
                "started_at": datetime.now(timezone.utc).isoformat(),
            }
            self._save(state)
            fcntl.flock(lock.fileno(), fcntl.LOCK_UN)
        try:
            yield lease_id
        finally:
            with self.lock_path.open("a+", encoding="utf-8") as lock:
                fcntl.flock(lock.fileno(), fcntl.LOCK_EX)
                state = self._prune(self._load())
                state.pop(lease_id, None)
                self._save(state)
                fcntl.flock(lock.fileno(), fcntl.LOCK_UN)
