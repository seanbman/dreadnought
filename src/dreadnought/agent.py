from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
from typing import Any, Protocol

from .order import Order


class AgentAdapter(Protocol):
    id: str
    requires_network: bool
    environment_allowlist: tuple[str, ...]

    def command(
        self,
        *,
        order: Order,
        order_path: Path,
        result_path: Path,
        scratch: Path,
        workspace: Path,
    ) -> list[str]: ...

    def usage_from_output(self, stdout: str) -> dict[str, Any] | None: ...


def _render_arg(arg: str, substitutions: dict[str, str]) -> str:
    rendered = arg
    for token, value in substitutions.items():
        rendered = rendered.replace(token, value)
    return rendered


def _minion_prompt(order: Order, order_path: Path, result_path: Path, scratch: Path, workspace: Path) -> str:
    return (
        "You are a subordinate Dreadnought minion executing a compartmentalized Project Arm Order. "
        f"Read the authoritative order JSON at {order_path}. The canonical workspace is {workspace} and is read-only; "
        f"use writable scratch at {scratch}. Do not mutate Grapher directly. Complete only the bounded objective: {order.objective!r}. "
        f"Before exit, write agent testimony as JSONL to {result_path}. Each line must be one Dreadnought protocol schema_version 1 "
        "record with perspective 'agent' and kind claim, action, artifact, requirement, risk, or note. "
        "For every acceptance criterion you assert is satisfied, emit at least one claim with data.acceptance_ref set to the criterion "
        "index (zero-based) or exact criterion text, plus a deterministic verifier. Supported verifier forms are "
        "filesystem.path with payload {'path':'relative/or/absolute','predicate':'exists|absent'}, "
        "filesystem.sha256 with payload {'path':'...','expected':'sha256'}, and process.command with payload "
        "{'argv':['command', 'arg'], 'expected_exit':0}. Example claim data: "
        "{'predicate':'succeeds','acceptance_ref':0,'verifier':'process.command','payload':{'argv':['pytest','-q'],'expected_exit':0}}. "
        "Dreadnought will execute verification independently after you exit; unsupported or missing verification remains unverified. "
        "For a simple summary, use kind 'note' with data {'audience':'human','text':'...'} and include the order_ref. "
        "Do not claim observer or evaluation authority."
    )


@dataclass(frozen=True)
class CommandAgentAdapter:
    """Adapter for an external agent exposed as a command-line program.

    Template tokens make provider wrappers deterministic. `{usage}` points to an
    optional JSON file where an adapter may report exact provider token counts.
    """

    id: str
    executable: str
    args: tuple[str, ...] = ()
    requires_network: bool = False
    environment_allowlist: tuple[str, ...] = ()

    def command(
        self,
        *,
        order: Order,
        order_path: Path,
        result_path: Path,
        scratch: Path,
        workspace: Path,
    ) -> list[str]:
        if not self.id.strip() or not self.executable.strip():
            raise ValueError("adapter id and executable must not be empty")
        usage_path = result_path.with_suffix(".usage.json")
        substitutions = {
            "{order}": str(order_path),
            "{result}": str(result_path),
            "{usage}": str(usage_path),
            "{scratch}": str(scratch),
            "{workspace}": str(workspace),
            "{project_arm}": order.project_arm,
            "{objective}": order.objective,
        }
        rendered = [_render_arg(arg, substitutions) for arg in self.args]
        return [self.executable, *rendered]

    def usage_from_output(self, stdout: str) -> dict[str, Any] | None:
        return None


@dataclass(frozen=True)
class CodexMinionAdapter:
    executable: str = "codex"
    id: str = "codex"
    requires_network: bool = True
    environment_allowlist: tuple[str, ...] = ("HOME", "XDG_CONFIG_HOME", "OPENAI_API_KEY", "CODEX_HOME")

    def command(
        self,
        *,
        order: Order,
        order_path: Path,
        result_path: Path,
        scratch: Path,
        workspace: Path,
    ) -> list[str]:
        prompt = _minion_prompt(order, order_path, result_path, scratch, workspace)
        return [
            self.executable,
            "exec",
            "--ephemeral",
            "--json",
            "--sandbox",
            "danger-full-access",
            prompt,
        ]

    def usage_from_output(self, stdout: str) -> dict[str, Any] | None:
        report: dict[str, Any] | None = None
        for raw in stdout.splitlines():
            try:
                event = json.loads(raw)
            except json.JSONDecodeError:
                continue
            if event.get("type") != "turn.completed" or not isinstance(event.get("usage"), dict):
                continue
            usage = event["usage"]
            report = {
                "input_tokens": int(usage.get("input_tokens") or 0),
                "output_tokens": int(usage.get("output_tokens") or 0),
                "cached_tokens": int(usage.get("cached_input_tokens") or usage.get("cached_tokens") or 0),
                "reasoning_tokens": int(usage.get("reasoning_tokens") or 0),
                "provider": "openai-codex-cli",
            }
        return report


@dataclass(frozen=True)
class CursorMinionAdapter:
    executable: str = "agent"
    id: str = "cursor"
    requires_network: bool = True
    environment_allowlist: tuple[str, ...] = ("HOME", "XDG_CONFIG_HOME", "CURSOR_API_KEY")

    def command(
        self,
        *,
        order: Order,
        order_path: Path,
        result_path: Path,
        scratch: Path,
        workspace: Path,
    ) -> list[str]:
        prompt = _minion_prompt(order, order_path, result_path, scratch, workspace)
        return [self.executable, "-p", "--output-format", "stream-json", prompt]

    def usage_from_output(self, stdout: str) -> dict[str, Any] | None:
        report: dict[str, Any] | None = None
        for raw in stdout.splitlines():
            try:
                event = json.loads(raw)
            except json.JSONDecodeError:
                continue
            if event.get("type") != "result":
                continue
            usage = event.get("usage")
            if not isinstance(usage, dict) and isinstance(event.get("result"), dict):
                usage = event["result"].get("usage")
            if not isinstance(usage, dict):
                continue
            report = {
                "input_tokens": int(usage.get("input_tokens") or usage.get("inputTokens") or 0),
                "output_tokens": int(usage.get("output_tokens") or usage.get("outputTokens") or 0),
                "cached_tokens": int(usage.get("cached_tokens") or usage.get("cachedTokens") or 0),
                "reasoning_tokens": int(usage.get("reasoning_tokens") or usage.get("reasoningTokens") or 0),
                "provider": "cursor-cli",
            }
        return report


def configured_minion_adapter(agent_type: str, executable: str | None = None) -> AgentAdapter:
    normalized = agent_type.strip().lower()
    if normalized == "codex":
        return CodexMinionAdapter(executable=executable or "codex")
    if normalized == "cursor":
        return CursorMinionAdapter(executable=executable or "agent")
    raise ValueError(
        f"no first-class minion adapter for {agent_type!r}; configure a CommandAgentAdapter explicitly"
    )
