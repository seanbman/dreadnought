from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable
import hashlib
import subprocess

from .protocol import Predicate, VerdictStatus


@dataclass(frozen=True)
class VerificationResult:
    status: VerdictStatus
    observed: Any = None
    evidence: dict[str, Any] | None = None
    reason: str | None = None


Verifier = Callable[[dict[str, Any]], VerificationResult]


class VerifierRegistry:
    def __init__(self) -> None:
        self._verifiers: dict[str, Verifier] = {}

    def register(self, name: str, verifier: Verifier) -> None:
        if not name.strip():
            raise ValueError("verifier name must not be empty")
        self._verifiers[name] = verifier

    def verify(self, name: str, payload: dict[str, Any]) -> VerificationResult:
        verifier = self._verifiers.get(name)
        if verifier is None:
            return VerificationResult(
                status=VerdictStatus.UNVERIFIABLE,
                reason=f"unknown verifier: {name}",
            )
        return verifier(payload)


def verify_path(payload: dict[str, Any]) -> VerificationResult:
    raw_path = payload.get("path")
    raw_predicate = payload.get("predicate")
    if not isinstance(raw_path, str) or not raw_path:
        return VerificationResult(VerdictStatus.MALFORMED, reason="path is required")
    try:
        predicate = Predicate(raw_predicate)
    except (TypeError, ValueError):
        return VerificationResult(VerdictStatus.MALFORMED, reason="recognized predicate is required")

    path = Path(raw_path)
    exists = path.exists()
    if predicate is Predicate.EXISTS:
        ok = exists
    elif predicate is Predicate.ABSENT:
        ok = not exists
    else:
        return VerificationResult(
            VerdictStatus.UNVERIFIABLE,
            observed={"exists": exists},
            reason=f"predicate {predicate.value} is not supported by path verifier",
        )
    return VerificationResult(
        VerdictStatus.SUPPORTED if ok else VerdictStatus.CONTRADICTED,
        observed={"exists": exists},
        evidence={"type": "filesystem", "path": str(path)},
    )


def verify_sha256(payload: dict[str, Any]) -> VerificationResult:
    raw_path = payload.get("path")
    expected = payload.get("expected")
    if not isinstance(raw_path, str) or not raw_path or not isinstance(expected, str) or not expected:
        return VerificationResult(VerdictStatus.MALFORMED, reason="path and expected hash are required")
    path = Path(raw_path)
    if not path.is_file():
        return VerificationResult(
            VerdictStatus.CONTRADICTED,
            observed={"exists": path.exists(), "is_file": path.is_file()},
            evidence={"type": "filesystem", "path": str(path)},
        )
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    return VerificationResult(
        VerdictStatus.SUPPORTED if digest == expected else VerdictStatus.CONTRADICTED,
        observed={"sha256": digest},
        evidence={"type": "hash", "algorithm": "sha256", "path": str(path), "sha256": digest},
    )


def verify_command(payload: dict[str, Any]) -> VerificationResult:
    argv = payload.get("argv")
    expected_exit = payload.get("expected_exit", 0)
    timeout = payload.get("timeout", 30)
    if not isinstance(argv, list) or not argv or not all(isinstance(item, str) and item for item in argv):
        return VerificationResult(VerdictStatus.MALFORMED, reason="argv must be a non-empty string array")
    if not isinstance(expected_exit, int):
        return VerificationResult(VerdictStatus.MALFORMED, reason="expected_exit must be an integer")
    try:
        completed = subprocess.run(
            argv,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        return VerificationResult(VerdictStatus.UNVERIFIABLE, reason=str(exc))
    ok = completed.returncode == expected_exit
    evidence = {
        "type": "command",
        "argv": argv,
        "exit_code": completed.returncode,
        "stdout": completed.stdout,
        "stderr": completed.stderr,
    }
    return VerificationResult(
        VerdictStatus.SUPPORTED if ok else VerdictStatus.CONTRADICTED,
        observed={"exit_code": completed.returncode},
        evidence=evidence,
    )


def default_registry() -> VerifierRegistry:
    registry = VerifierRegistry()
    registry.register("filesystem.path", verify_path)
    registry.register("filesystem.sha256", verify_sha256)
    registry.register("process.command", verify_command)
    return registry
