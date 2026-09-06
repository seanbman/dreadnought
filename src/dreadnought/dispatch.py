from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import json

from .agent import AgentAdapter
from .grapher import GrapherControlPlane
from .order import Order
from .protocol import ObservationType, Perspective, ProtocolRecord, RecordKind
from .result_channel import AgentResultChannel
from .sarcophagus import Sarcophagus


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


class ProjectArmDispatcher:
    """Dispatch one compartmentalized Order to one external agent adapter."""

    def __init__(
        self,
        *,
        workspace: Path,
        scratch: Path,
        sarcophagus: Sarcophagus | None = None,
        grapher: GrapherControlPlane | None = None,
        result_channel: AgentResultChannel | None = None,
    ) -> None:
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
        order_path.write_text(json.dumps(order.to_dict(), indent=2) + "\n", encoding="utf-8")
        if result_path.exists():
            result_path.unlink()

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

        return DispatchResult(
            order_id=order.id,
            project_arm=order.project_arm,
            adapter_id=adapter.id,
            exit_code=completed.returncode,
            stdout=completed.stdout,
            stderr=completed.stderr,
            observation_id=observation.id,
            agent_record_ids=tuple(record.id for record in agent_records),
        )
