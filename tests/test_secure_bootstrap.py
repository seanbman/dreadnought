from pathlib import Path

import pytest


def test_kernel_cli_seeds_primary_codex_with_bootstrap_instruction(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from dreadnought.config import configure_agent, default_config, save_config
    from dreadnought.kernel import run_kernel_cli
    (tmp_path / ".dreadnought" / "missions").mkdir(parents=True)
    (tmp_path / ".dreadnought" / "INSTRUCTIONS.md").write_text("instructions")
    config = default_config(tmp_path)
    config["bootstrap_mission"] = "mission-test"
    config["instructions_path"] = ".dreadnought/INSTRUCTIONS.md"
    save_config(tmp_path, config)
    configure_agent(tmp_path, agent_type="codex", executable="codex", args=[], primary=True)
    seen = {}
    def fake_run(self, *, agent_type, executable, args):
        seen["args"] = args
        return 0
    monkeypatch.setattr("dreadnought.kernel.PrimaryKernel.run", fake_run)
    assert run_kernel_cli(["launch", "--agent-type", "codex", "--root", str(tmp_path)]) == 0
    assert "Begin immediately" in seen["args"][-1]
    assert ".dreadnought/INSTRUCTIONS.md" in seen["args"][-1]
    assert "mission-test.json" in seen["args"][-1]
