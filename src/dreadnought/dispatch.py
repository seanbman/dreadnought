from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import json

from .agent import AgentAdapter
from .config import load_config
from .grapher import GrapherControlPlane
from .order import Order
from .protocol import ObservationType, Perspective, ProtocolRecord, RecordKind
from .result_channel import AgentResultChannel
from .sarcophagus import Sarcophagus
from .usage import TokenUsage, TokenUsageLedger


@dataclass(frozen=True)
class DispatchResult:
    order_id: str
    project_arm: str
    adapter_id: str
    exit_code: int
    stdout: str
    stderr: str
    observation_id: str
    agent_record_ids: tuple[str, ...] = ()
    usage_id: str | None = None


class ProjectArmDispatcher:
    """Dispatch one compartmentalized Order to one external agent adapter."""

    def __init__(self, *, workspace: Path, scratch: Path,
                 sarcophagus: Sarcophagus | None = None,
                 grapher: GrapherControlPlane | None = None,
                 result_channel: AgentResultChannel | None = None) -> None:
        self.workspace = workspace.resolve()
        self.scratch = scratch.resolve()
        self.sarcophagus = sarcophagus or Sarcophagus(self.workspace, self.scratch)
        self.grapher = grapher or GrapherControlPlane(self.workspace)
        self.result_channel = result_channel or AgentResultChannel()

    def dispatch(self, order: Order, adapter: AgentAdapter, *, timeout: int = 300) -> DispatchResult:
        errors = order.validate()
        if errors:
            raise ValueError("invalid order: " + "; ".join(errors))

        packet_dir = self.scratch / "orders"
        result_dir = self.scratch / "results"
        packet_dir.mkdir(parents=True, exist_ok=True)
        result_dir.mkdir(parents=True, exist_ok=True)
        order_path = packet_dir / f"{order.id}.json"
        result_path = result_dir / f"{order.id}.jsonl"
        usage_path = result_path.with_suffix(".usage.json")
        order_path.write_text(json.dumps(order.to_dict(), indent=2) + "\n", encoding="utf-8")
        for stale in (result_path, usage_path):
            if stale.exists():
                stale.unlink()

        command = adapter.command(
            order=order,
            order_path=order_path,
            result_path=result_path,
            scratch=self.scratch,
            workspace=self.workspace,
        )
        completed = self.sarcophagus.run(command, timeout=timeout)

        observation = ProtocolRecord.create(
            kind=RecordKind.OBSERVATION,
            perspective=Perspective.OBSERVER,
            actor_id="dreadnought:observer",
            order_ref=order.id,
            subject_ref=f"dispatch:{order.project_arm}",
            data={
                "observation_type": ObservationType.PROCESS.value,
                "result": {
                    "adapter_id": adapter.id,
                    "argv": command,
                    "exit_code": completed.returncode,
                    "stdout": completed.stdout,
                    "stderr": completed.stderr,
                    "result_path": str(result_path),
                    "usage_path": str(usage_path),
                },
            },
        )
        self.grapher.write_record(observation)

        agent_records = self.result_channel.read(result_path)
        for record in agent_records:
            if record.order_ref is None:
                record.order_ref = order.id
            elif record.order_ref != order.id:
                raise ValueError(f"agent result references wrong order: {record.order_ref}")
            self.grapher.write_record(record)

        usage_id = self._record_usage_if_reported(usage_path, order, adapter.id)
        return DispatchResult(
            order_id=order.id,
            project_arm=order.project_arm,
            adapter_id=adapter.id,
            exit_code=completed.returncode,
            stdout=completed.stdout,
            stderr=completed.stderr,
            observation_id=observation.id,
            agent_record_ids=tuple(record.id for record in agent_records),
            usage_id=usage_id,
        )

    def _record_usage_if_reported(self, usage_path: Path, order: Order, adapter_id: str) -> str | None:
        if not usage_path.is_file():
            return None
        try:
            report = json.loads(usage_path.read_text(encoding="utf-8"))
            input_tokens = int(report["input_tokens"])
            output_tokens = int(report["output_tokens"])
        except (OSError, json.JSONDecodeError, KeyError, TypeError, ValueError) as exc:
            raise ValueError(f"invalid adapter usage report {usage_path}: {exc}") from exc
        config = load_config(self.workspace)
        usage = TokenUsage.create(
            agent_id=str(report.get("agent_id") or adapter_id),
            agent_role="minion",
            project_id=str(report.get("project_id") or config.get("project_id") or self.workspace.name),
            task_id=order.id,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cached_tokens=int(report.get("cached_tokens") or 0),
            reasoning_tokens=int(report.get("reasoning_tokens") or 0),
            provider=report.get("provider"),
            model=report.get("model"),
            source="adapter_report",
        )
        TokenUsageLedger(self.workspace).record(usage)
        return usage.id
