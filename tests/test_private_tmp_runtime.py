from pathlib import Path

import pytest

from dreadnought.kernel import PrimaryKernel


def test_primary_kernel_uses_private_writable_tmp(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    seen = {}
    codex_home = tmp_path.parent / "codex-home"
    monkeypatch.setenv("CODEX_HOME", str(codex_home))
    monkeypatch.setattr("dreadnought.kernel.shutil.which", lambda name: "/usr/bin/bwrap")
    monkeypatch.setattr(PrimaryKernel, "_bubblewrap_probe", staticmethod(lambda backend: (True, None)))

    def fake_call(argv, *, cwd, env):
        seen["argv"] = list(argv)
        seen["env"] = dict(env)
        return 0

    monkeypatch.setattr("dreadnought.kernel.subprocess.call", fake_call)
    assert PrimaryKernel(tmp_path).run(agent_type="codex", executable="codex", args=[]) == 0

    argv = seen["argv"]
    assert ("--tmpfs", "/tmp") in list(zip(argv, argv[1:]))
    assert seen["env"]["TMPDIR"] == "/tmp"
