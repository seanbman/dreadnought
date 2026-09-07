from __future__ import annotations

from typing import Iterable

from prompt_toolkit import PromptSession
from prompt_toolkit.key_binding import KeyBindings


_HELP_TEXT = """Dreadnought interactive controls

  ↑ / ↓       move through a numbered menu
  1..N        select an item directly
  Enter       accept the current selection
  q           back / exit a menu
  Esc         cancel the current prompt and exit cleanly
  Ctrl-C      cancel the current prompt and exit cleanly

Command help:
  dreadnought help
  dreadnought --help
  man dreadnought
"""


def _prompt(text: str, default: str = "", option_count: int | None = None) -> str | None:
    bindings = KeyBindings()
    state = {"index": 0}

    def _set_choice(event, delta: int) -> None:
        if not option_count:
            return
        state["index"] = (state["index"] + delta) % option_count
        value = str(state["index"] + 1)
        event.current_buffer.text = value
        event.current_buffer.cursor_position = len(value)

    @bindings.add("up")
    def _up(event) -> None:
        _set_choice(event, -1)

    @bindings.add("down")
    def _down(event) -> None:
        _set_choice(event, 1)

    @bindings.add("escape")
    @bindings.add("c-c")
    def _cancel(event) -> None:
        event.app.exit(exception=KeyboardInterrupt())

    session = PromptSession(key_bindings=bindings)
    try:
        return session.prompt(text, default=default)
    except (EOFError, KeyboardInterrupt):
        return None


def choose(title: str, text: str, options: Iterable[tuple[str, str]]) -> str | None:
    values = list(options)
    top_level = title == "Dreadnought"
    if top_level and not any(value == "help" for value, _ in values):
        exit_items = [item for item in values if item[0] == "exit"]
        values = [item for item in values if item[0] != "exit"]
        values.append(("help", "Help"))
        values.extend(exit_items)
    if not values:
        return None

    while True:
        print(f"\n{title}\n{text}")
        for index, (_, label) in enumerate(values, start=1):
            print(f"  {index}. {label}")
        print("  q. Back / Exit")
        answer = _prompt(f"Select [1-{len(values)}, q]: ", option_count=len(values))
        if answer is None:
            return None
        normalized = answer.strip().lower()
        if normalized in {"q", "quit", "exit", "back"}:
            return None
        if normalized.isdigit():
            index = int(normalized) - 1
            if 0 <= index < len(values):
                value = values[index][0]
                if top_level and value == "help":
                    show("Dreadnought help", _HELP_TEXT.rstrip())
                    continue
                return value
        print("Invalid selection. Use a number, ↑/↓ then Enter, or q to exit.")


def ask(title: str, text: str, default: str = "") -> str | None:
    print(f"\n{title}")
    suffix = f" [{default}]" if default else ""
    answer = _prompt(f"{text}{suffix}: ")
    if answer is None:
        raise SystemExit(0)
    normalized = answer.strip().lower()
    if normalized in {"q", "quit", "exit", "back"}:
        raise SystemExit(0)
    return answer if answer else default


def confirm(title: str, text: str) -> bool | None:
    print(f"\n{title}")
    while True:
        answer = _prompt(f"{text} [y/n, q]: ")
        if answer is None:
            raise SystemExit(0)
        normalized = answer.strip().lower()
        if normalized in {"q", "quit", "exit", "back"}:
            raise SystemExit(0)
        if normalized in {"y", "yes"}:
            return True
        if normalized in {"n", "no"}:
            return False
        print("Please enter y, n, or q.")


def show(title: str, text: str) -> None:
    print(f"\n{title}\n{text}")
