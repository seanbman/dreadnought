from __future__ import annotations

import sys

from dreadnought import main as main_module


def test_help_command_prints_controls_and_manual(monkeypatch, capsys):
    monkeypatch.setattr(sys, "argv", ["dreadnought", "help"])
    monkeypatch.setattr(sys.stdin, "isatty", lambda: False)
    monkeypatch.setattr(sys.stdout, "isatty", lambda: False)

    assert main_module.main() == 0
    output = capsys.readouterr().out
    assert "Dreadnought agent control plane" in output
    assert "Interactive controls:" in output
    assert "man dreadnought" in output
