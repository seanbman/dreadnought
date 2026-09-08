from __future__ import annotations

import json
from pathlib import Path

import pytest

from dreadnought.config import configure_agent, load_config
from dreadnought.kernel import PrimaryKernel
from dreadnought.limits import MinionSlotManager
from dreadnought.mission import Mission
from dreadnought.project_policy import project_policy
from dreadnought.secure_bootstrap import run_bootstrap_cli
from dreadnought.usage import TokenUsageLedger


def test_agent_config_is_kernelized_and_preserves_provider_command(tmp_path: Path) -> None:
    configure_agent(tmp_path, agent_type="codex", executable="codex", args=["--model", "x"], primary=True)
    config = load_config(tmp_path)
    agent = config["agents"]["codex"]
    assert agent["executable"] == "dreadnought"
    assert agent["args"] == ["kernel", "launch", "--agent-type", "codex"]
    assert agent["provider_executable"] == "codex"
    assert agent["provider_args"] == ["--model", "x"]


def test_legacy_agent_config_is_kernelized_on_load(tmp_path: Path) -> None:
    config_dir = tmp_path / ".dreadnought"
    config_dir.mkdir()
    (config_dir / "config.json").write_text(json.dumps({
        "version": 2,
        "project_id": "demo",
        "agents": {"codex": {"type": "codex", "executable": "codex", "args": ["--foo"]}},
        "primary_agent": "codex",
    }))
    agent = load_config(tmp_path)["agents"]["codex"]
    assert agent["executable"] == "dreadnought"
    assert agent["provider_executable"] == "codex"
    assert agent["provider_args"] == ["--foo"]


def test_secure_init_persists_project_minion_cap_in_policy_and_mission(tmp_path: Path) -> None:
    rc = run_bootstrap_cli([
        "Initialize a bounded project.",
        "--root", str(tmp_path),
        "--project-id", "demo",
        "--max-minions", "2",
        "--non-interactive",
    ])
    assert rc == 0
    config = load_config(tmp_path)
    assert project_policy(config, "demo").max_minions == 2
    mission = Mission.read(next((tmp_path / ".dreadnought" / "missions").glob("*.json")))
    assert mission.capabilities.max_minions == 2
    instructions = (tmp_path / ".dreadnought" / "INSTRUCTIONS.md").read_text()
    assert "canonical workspace and managed project are read-only" in instructions
    assert "Project max concurrent minions: `2`" in instructions


def test_minion_slots_enforce_project_scoped_concurrency(tmp_path: Path) -> None:
    manager = MinionSlotManager(tmp_path)
    with manager.lease("project-a", 1):
        with pytest.raises(RuntimeError, match="max_minions=1"):
            with manager.lease("project-a", 1):
                pass
        with manager.lease("project-b", 1):
            pass


def test_live_unmetered_primary_session_is_visible_immediately(tmp_path: Path) -> None:
    ledger = TokenUsageLedger(tmp_path)
    session_id = ledger.mark_active_session(agent_id="codex", agent_role="primary", project_id="demo")
    stats = ledger.stats()
    assert stats["metering"]["complete"] is False
    assert stats["metering"]["active_unmetered_sessions"] == 1
    assert stats["metering"]["active_sessions"][0]["id"] == session_id
    ledger.clear_active_session(session_id)
    assert TokenUsageLedger(tmp_path).stats()["metering"]["active_unmetered_sessions"] == 0


def test_primary_kernel_doctor_requires_operational_bubblewrap(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("dreadnought.kernel.shutil.which", lambda name: "/usr/bin/bwrap")
    monkeypatch.setattr(PrimaryKernel, "_bubblewrap_probe", staticmethod(lambda backend: (False, "uid map denied")))
    status = PrimaryKernel(tmp_path).doctor()
    assert status["available"] is False
    assert status["detail"] == "uid map denied"


def test_primary_kernel_builds_read_only_workspace_and_strips_git_credentials(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    seen = {}
    codex_home = tmp_path.parent / f"{tmp_path.name}-codex-home"
    monkeypatch.setenv("GITHUB_TOKEN", "secret")
    monkeypatch.setenv("OPENAI_API_KEY", "provider")
    monkeypatch.setenv("CODEX_HOME", str(codex_home))
    monkeypatch.setattr("dreadnought.kernel.shutil.which", lambda name: "/usr/bin/bwrap")
    monkeypatch.setattr(PrimaryKernel, "_bubblewrap_probe", staticmethod(lambda backend: (True, None)))

    def fake_call(argv, *, cwd, env):
        seen["argv"] = argv
        seen["cwd"] = cwd
        seen["env"] = env
        return 0

    monkeypatch.setattr("dreadnought.kernel.subprocess.call", fake_call)
    rc = PrimaryKernel(tmp_path).run(agent_type="codex", executable="codex", args=[])
    assert rc == 0
    argv = seen["argv"]
    triples = list(zip(argv, argv[1:], argv[2:]))
    resolved_codex_home = str(codex_home.resolve())
    assert ("--ro-bind", str(tmp_path), str(tmp_path)) in triples
    assert ("--bind", resolved_codex_home, resolved_codex_home) in triples
    assert "GITHUB_TOKEN" not in seen["env"]
    assert seen["env"]["OPENAI_API_KEY"] == "provider"
    assert seen["env"]["CODEX_HOME"] == resolved_codex_home
    assert seen["env"]["DREADNOUGHT_CONTROL_SOCKET"].endswith("control.sock")


def test_primary_kernel_rejects_codex_home_inside_workspace(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CODEX_HOME", str(tmp_path / ".codex"))
    monkeypatch.setattr("dreadnought.kernel.shutil.which", lambda name: "/usr/bin/bwrap")
    monkeypatch.setattr(PrimaryKernel, "_bubblewrap_probe", staticmethod(lambda backend: (True, None)))
    with pytest.raises(ValueError, match="outside the read-only canonical workspace"):
        PrimaryKernel(tmp_path).run(agent_type="codex", executable="codex", args=[])


def test_primary_kernel_cannot_write_canonical_workspace(tmp_path: Path) -> None:
    kernel = PrimaryKernel(tmp_path)
    if not kernel.doctor()["available"]:
        pytest.skip("bubblewrap sandbox is not operational")
    target = tmp_path / "protected.txt"
    target.write_text("original")
    command = ["-c", f"echo hacked > {target}"]
    rc = kernel.run(agent_type="custom", executable="/bin/sh", args=command)
    assert rc != 0
    assert target.read_text() == "original"
