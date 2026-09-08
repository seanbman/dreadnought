from __future__ import annotations

from contextlib import contextmanager
from pathlib import Path
import subprocess
import tomllib

import pytest

from dreadnought.codex_compat import CodexCompatibilityError, codex_system_requirements_overlay, pin_unified_exec_requirement
from dreadnought.kernel import PrimaryKernel
from dreadnought.sarcophagus import Sarcophagus


def test_pin_unified_exec_requirement_preserves_existing_policy() -> None:
    original = """allowed_sandbox_modes = [\"read-only\"]

[features]
personality = true
unified_exec = true
"""
    rendered = pin_unified_exec_requirement(original)
    parsed = tomllib.loads(rendered)
    assert parsed["allowed_sandbox_modes"] == ["read-only"]
    assert parsed["features"]["personality"] is True
    assert parsed["features"]["unified_exec"] is False


def test_pin_unified_exec_requirement_adds_feature_table() -> None:
    rendered = pin_unified_exec_requirement("allowed_sandbox_modes = [\"read-only\"]\n")
    parsed = tomllib.loads(rendered)
    assert parsed["allowed_sandbox_modes"] == ["read-only"]
    assert parsed["features"]["unified_exec"] is False


def test_pin_unified_exec_requirement_fails_closed_on_inline_feature_policy() -> None:
    with pytest.raises(CodexCompatibilityError, match="unsupported inline/dotted"):
        pin_unified_exec_requirement("features = { unified_exec = true }\n")


def test_codex_system_overlay_preserves_source_and_is_ephemeral(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    source = tmp_path / "system-codex"
    source.mkdir()
    requirements = source / "requirements.toml"
    requirements.write_text(
        "allowed_sandbox_modes = [\"read-only\"]\n\n[features]\nunified_exec = true\n",
        encoding="utf-8",
    )
    monkeypatch.setattr("dreadnought.codex_compat.CODEX_SYSTEM_DIR", source)

    overlay_path: Path | None = None
    with codex_system_requirements_overlay() as overlay:
        overlay_path = overlay
        parsed = tomllib.loads((overlay / "requirements.toml").read_text(encoding="utf-8"))
        assert parsed["allowed_sandbox_modes"] == ["read-only"]
        assert parsed["features"]["unified_exec"] is False
        assert "unified_exec = true" in requirements.read_text(encoding="utf-8")

    assert overlay_path is not None
    assert not overlay_path.exists()


def test_primary_kernel_mounts_codex_requirements_before_private_tmp(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    codex_home = tmp_path / "codex-home"
    overlay = tmp_path / "overlay"
    overlay.mkdir()
    seen: dict[str, object] = {}

    @contextmanager
    def fake_overlay():
        yield overlay

    def fake_call(argv, *, cwd, env):
        seen["argv"] = list(argv)
        seen["cwd"] = cwd
        seen["env"] = env
        return 0

    monkeypatch.setenv("CODEX_HOME", str(codex_home))
    monkeypatch.setattr("dreadnought.kernel.shutil.which", lambda name: "/usr/bin/bwrap")
    monkeypatch.setattr(PrimaryKernel, "_bubblewrap_probe", staticmethod(lambda backend: (True, None)))
    monkeypatch.setattr(PrimaryKernel, "_credential_masks", staticmethod(lambda: []))
    monkeypatch.setattr("dreadnought.kernel.codex_system_requirements_overlay", fake_overlay)
    monkeypatch.setattr("dreadnought.kernel.subprocess.call", fake_call)

    assert PrimaryKernel(workspace).run(agent_type="codex", executable="codex", args=[]) == 0
    argv = seen["argv"]
    assert isinstance(argv, list)
    triples = list(zip(argv, argv[1:], argv[2:]))
    assert ("--ro-bind", str(overlay), "/etc/codex") in triples
    overlay_index = argv.index(str(overlay))
    tmp_index = argv.index("/tmp")
    assert overlay_index < tmp_index


def test_sarcophagus_mounts_codex_requirements_before_private_tmp(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    scratch = tmp_path / "scratch"
    overlay = tmp_path / "overlay"
    overlay.mkdir()
    seen: dict[str, object] = {}

    @contextmanager
    def fake_overlay():
        yield overlay

    def fake_run(argv, *, cwd, env, capture_output, text, timeout, check):
        seen["argv"] = list(argv)
        return subprocess.CompletedProcess(argv, 0, "", "")

    monkeypatch.setattr("dreadnought.sarcophagus.shutil.which", lambda name: "/usr/bin/bwrap")
    monkeypatch.setattr("dreadnought.sarcophagus.codex_system_requirements_overlay", fake_overlay)
    monkeypatch.setattr("dreadnought.sarcophagus.subprocess.run", fake_run)

    completed = Sarcophagus(workspace, scratch).run(["codex", "exec", "hello"])
    assert completed.returncode == 0
    argv = seen["argv"]
    assert isinstance(argv, list)
    triples = list(zip(argv, argv[1:], argv[2:]))
    assert ("--ro-bind", str(overlay), "/etc/codex") in triples
    overlay_index = argv.index(str(overlay))
    tmp_index = argv.index("/tmp")
    assert overlay_index < tmp_index
