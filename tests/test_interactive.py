from __future__ import annotations

import pytest

from dreadnought import interactive


def test_choose_accepts_number(monkeypatch):
    monkeypatch.setattr(interactive, "_prompt", lambda *args, **kwargs: "2")
    assert interactive.choose("Menu", "Pick", [("one", "One"), ("two", "Two")]) == "two"


def test_choose_q_returns_to_caller(monkeypatch):
    monkeypatch.setattr(interactive, "_prompt", lambda *args, **kwargs: "q")
    assert interactive.choose("Menu", "Pick", [("one", "One")]) is None


def test_top_level_help_is_inline(monkeypatch, capsys):
    answers = iter(["1", "q"])
    monkeypatch.setattr(interactive, "_prompt", lambda *args, **kwargs: next(answers))
    assert interactive.choose("Dreadnought", "Project: demo", [("exit", "Exit")]) is None
    output = capsys.readouterr().out
    assert "Dreadnought help" in output
    assert "man dreadnought" in output


def test_text_prompt_cancellation_exits_cleanly(monkeypatch):
    monkeypatch.setattr(interactive, "_prompt", lambda *args, **kwargs: None)
    with pytest.raises(SystemExit) as exc:
        interactive.ask("Dreadnought setup", "Project ID", "demo")
    assert exc.value.code == 0


def test_confirm_q_exits_cleanly(monkeypatch):
    monkeypatch.setattr(interactive, "_prompt", lambda *args, **kwargs: "q")
    with pytest.raises(SystemExit) as exc:
        interactive.confirm("Dreadnought setup", "Continue?")
    assert exc.value.code == 0
