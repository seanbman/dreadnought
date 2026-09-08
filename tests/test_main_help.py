from __future__ import annotations

import sys

import pytest

from dreadnought import main as main_module


@pytest.mark.parametrize("flag", ["help", "--help", "-h"])
def test_help_command_prints_bootstrap_contract_and_controls(monkeypatch, capsys, flag):
    monkeypatch.setattr(sys, "argv", ["dreadnought", flag])
    monkeypatch.setattr(sys.stdin, "isatty", lambda: False)
    monkeypatch.setattr(sys.stdout, "isatty", lambda: False)

    assert main_module.main() == 0
    output = capsys.readouterr().out
    assert "Dreadnought agent control plane" in output
    assert "dreadnought initialize [brief]" in output
    assert "initialize/adopt a workspace and generate instructions" in output
    assert "Interactive controls:" in output
    assert "man dreadnought" in output
