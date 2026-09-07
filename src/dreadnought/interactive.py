from __future__ import annotations

from typing import Iterable

from prompt_toolkit.shortcuts import input_dialog, message_dialog, radiolist_dialog, yes_no_dialog


def choose(title: str, text: str, options: Iterable[tuple[str, str]]) -> str | None:
    return radiolist_dialog(title=title, text=text, values=list(options)).run()


def ask(title: str, text: str, default: str = "") -> str | None:
    return input_dialog(title=title, text=text, default=default).run()


def confirm(title: str, text: str) -> bool:
    return bool(yes_no_dialog(title=title, text=text).run())


def show(title: str, text: str) -> None:
    message_dialog(title=title, text=text).run()
