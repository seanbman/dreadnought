from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from .order import Order


class AgentAdapter(Protocol):
    id: str

    def command(
        self,
        *,
        order: Order,
        order_path: Path,
        result_path: Path,
        scratch: Path,
        workspace: Path,
    ) -> list[str]: ...


@dataclass(frozen=True)
class CommandAgentAdapter:
    """Adapter for an external agent exposed as a command-line program.

    Template tokens make provider wrappers deterministic. `{usage}` points to an
    optional JSON file where an adapter may report exact provider token counts.
    """

    id: str
    executable: str
    args: tuple[str, ...] = ()

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
        rendered = [substitutions.get(arg, arg) for arg in self.args]
        return [self.executable, *rendered]
