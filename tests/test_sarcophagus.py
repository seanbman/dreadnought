from pathlib import Path

import pytest

from dreadnought.sarcophagus import NetworkPolicy, Sarcophagus, SarcophagusPolicy, SarcophagusUnavailable


def test_rejects_scratch_inside_workspace(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    sandbox = Sarcophagus(workspace, workspace / "scratch")
    with pytest.raises(ValueError, match="outside"):
        sandbox.validate()


def test_rejects_writable_canonical_workspace(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    scratch = tmp_path / "scratch"
    workspace.mkdir()
    policy = SarcophagusPolicy(writable_paths=(str(workspace / "src"),))
    with pytest.raises(ValueError, match="canonical workspace"):
        Sarcophagus(workspace, scratch, policy).validate()


def test_plan_fails_closed_without_bubblewrap(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    monkeypatch.setattr("dreadnought.sarcophagus.shutil.which", lambda _: None)
    with pytest.raises(SarcophagusUnavailable, match="refusing unsandboxed"):
        Sarcophagus(workspace, tmp_path / "scratch").plan(["true"])


def test_plan_is_read_only_and_network_isolated_by_default(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    scratch = tmp_path / "scratch"
    monkeypatch.setattr("dreadnought.sarcophagus.shutil.which", lambda _: "/usr/bin/bwrap")
    plan = Sarcophagus(workspace, scratch).plan(["python", "-V"])
    argv = list(plan.argv)
    assert "--unshare-net" in argv
    assert ["--ro-bind", str(workspace.resolve()), str(workspace.resolve())] == argv[
        argv.index(str(workspace.resolve())) - 1 : argv.index(str(workspace.resolve())) + 2
    ]
    assert "--bind" in argv
    assert str(scratch.resolve()) in argv


def test_host_network_must_be_explicit(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    monkeypatch.setattr("dreadnought.sarcophagus.shutil.which", lambda _: "/usr/bin/bwrap")
    policy = SarcophagusPolicy(network=NetworkPolicy.HOST)
    plan = Sarcophagus(workspace, tmp_path / "scratch", policy).plan(["true"])
    assert "--unshare-net" not in plan.argv
