from pathlib import Path
import hashlib

from dreadnought.protocol import VerdictStatus
from dreadnought.verify import default_registry, verify_command, verify_path, verify_sha256


def test_unknown_verifier_is_unverifiable():
    result = default_registry().verify("missing", {})
    assert result.status is VerdictStatus.UNVERIFIABLE


def test_path_exists_and_absent(tmp_path: Path):
    target = tmp_path / "artifact.txt"
    target.write_text("ok")
    assert verify_path({"path": str(target), "predicate": "exists"}).status is VerdictStatus.SUPPORTED
    assert verify_path({"path": str(target), "predicate": "absent"}).status is VerdictStatus.CONTRADICTED


def test_sha256_verifier(tmp_path: Path):
    target = tmp_path / "artifact.txt"
    target.write_text("deterministic")
    expected = hashlib.sha256(target.read_bytes()).hexdigest()
    result = verify_sha256({"path": str(target), "expected": expected})
    assert result.status is VerdictStatus.SUPPORTED
    assert result.observed["sha256"] == expected


def test_command_exit_code():
    result = verify_command({"argv": ["python", "-c", "raise SystemExit(0)"], "expected_exit": 0})
    assert result.status is VerdictStatus.SUPPORTED
    assert result.observed == {"exit_code": 0}


def test_command_failure_is_contradicted():
    result = verify_command({"argv": ["python", "-c", "raise SystemExit(3)"], "expected_exit": 0})
    assert result.status is VerdictStatus.CONTRADICTED
