from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from pathlib import Path
from typing import Sequence
import os
import shutil
import subprocess


class IsolationBackend(StrEnum):
    BWRAP = "bubblewrap"


class NetworkPolicy(StrEnum):
    NONE = "none"
    HOST = "host"


@dataclass(frozen=True)
class SarcophagusPolicy:
    network: NetworkPolicy = NetworkPolicy.NONE
    writable_paths: tuple[str, ...] = ()
    environment_allowlist: tuple[str, ...] = ("PATH", "LANG", "LC_ALL", "TERM")


@dataclass(frozen=True)
class ExecutionPlan:
    backend: IsolationBackend
    argv: tuple[str, ...]
    cwd: str
    environment: dict[str, str] = field(default_factory=dict)


class SarcophagusUnavailable(RuntimeError):
    pass


class Sarcophagus:
    """Build and execute a Linux sandbox with the canonical workspace read-only.

    This prototype deliberately supports only Bubblewrap. It fails closed when
    the backend is unavailable rather than silently executing on the host. Each
    sandbox receives a private writable /tmp so provider runtimes can create
    ephemeral files without exposing the host temporary directory.
    """

    def __init__(self, workspace: Path, scratch: Path, policy: SarcophagusPolicy | None = None) -> None:
        self.workspace = workspace.resolve()
        self.scratch = scratch.resolve()
        self.policy = policy or SarcophagusPolicy()

    def validate(self) -> None:
        if not self.workspace.is_dir():
            raise ValueError("workspace must be an existing directory")
        if self.scratch == self.workspace or self.workspace in self.scratch.parents:
            raise ValueError("scratch must live outside the canonical workspace")
        for raw in self.policy.writable_paths:
            candidate = Path(raw).resolve()
            if candidate == self.workspace or self.workspace in candidate.parents:
                raise ValueError("writable paths must not include the canonical workspace")

    def plan(self, command: Sequence[str]) -> ExecutionPlan:
        self.validate()
        if not command or not all(isinstance(item, str) and item for item in command):
            raise ValueError("command must be a non-empty string sequence")
        backend = shutil.which("bwrap")
        if backend is None:
            raise SarcophagusUnavailable("bubblewrap is required; refusing unsandboxed execution")

        self.scratch.mkdir(parents=True, exist_ok=True)
        argv: list[str] = [
            backend,
            "--die-with-parent",
            "--new-session",
            "--proc", "/proc",
            "--dev", "/dev",
            "--ro-bind", "/", "/",
            "--tmpfs", "/tmp",
            "--ro-bind", str(self.workspace), str(self.workspace),
            "--bind", str(self.scratch), str(self.scratch),
            "--chdir", str(self.workspace),
        ]
        if self.policy.network is NetworkPolicy.NONE:
            argv.append("--unshare-net")
        for raw in self.policy.writable_paths:
            path = Path(raw).resolve()
            path.mkdir(parents=True, exist_ok=True)
            argv.extend(("--bind", str(path), str(path)))
        argv.extend(("--", *command))

        environment = {
            key: value
            for key, value in os.environ.items()
            if key in self.policy.environment_allowlist
        }
        environment["TMPDIR"] = "/tmp"
        return ExecutionPlan(
            backend=IsolationBackend.BWRAP,
            argv=tuple(argv),
            cwd=str(self.workspace),
            environment=environment,
        )

    def run(self, command: Sequence[str], *, timeout: int = 300) -> subprocess.CompletedProcess[str]:
        plan = self.plan(command)
        return subprocess.run(
            plan.argv,
            cwd=plan.cwd,
            env=plan.environment,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
