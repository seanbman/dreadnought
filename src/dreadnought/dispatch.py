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
from .sarcophagus import NetworkPolicy, Sarcophagus, SarcophagusPolicy
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
    project_id: str | None = None
    agent_record_ids: tuple[str, ...] = ()
    usage_id: str | None = None


class ProjectArmDispatcher:
    """Dispatch one compartmentalized Order to one project-scoped external agent.

    The constructor receives the Dreadnought workspace root. An Order with
    ``project_id`` is routed to that registered project's canonical root and Grapher
    brain without changing the workspace default project.
    """

    def __init__(
        self,
        *,
        workspace: Path,
        scratch: Path,
        sarcophagus: Sarcophagus | None = None,
        grapher: GrapherControlPlane | None = None,
        result_channel: AgentResultChannel | None = None,
    ) -> None:
        self.control_workspace = workspace.resolve()
        self.workspace = self.control_workspace
        self.scratch = scratch.resolve()
        self.sarcophagus = sarcophagus
        self.grapher = grapher
        self.result_channel = result_channel or AgentResultChannel()

    def dispatch(self, order: Order, adapter: AgentAdapter, *, timeout: int = 300) -> DispatchResult:
        errors = order.validate()
        if errors:
            raise ValueError("invalid order: " + "; ".join(errors))

        grapher = self.grapher or GrapherControlPlane(self.control_workspace, project_id=order.project_id)
        project_workspace = grapher.project_root
        project_scratch = self.scratch / order.project_id if order.project_id else self.scratch
        if self.sarcophagus is not None:
            sarcophagus = self.sarcophagus
        else:
            base_env = ("PATH", "LANG", "LC_ALL", "TERM")
            adapter_env = tuple(getattr(adapter, "environment_allowlist", ()) or ())
            policy = SarcophagusPolicy(
                network=NetworkPolicy.HOST if bool(getattr(adapter, "requires_network", False)) else NetworkPolicy.NONE,
                environment_allowlist=tuple(dict.fromkeys((*base_env, *adapter_env))),
            )
            sarcophagus = Sarcophagus(project_workspace, project_scratch, policy=policy)

        packet_dir = project_scratch / "orders"
        result_dir = project_scratch / "results"
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
            scratch=project_scratch,
            workspace=project_workspace,
        )
        completed = sarcophagus.run(command, timeout=timeout)

        observation = ProtocolRecord.create(
            kind=RecordKind.OBSERVATION,
            perspective=Perspective.OBSERVER,
            actor_id="dreadnought:observer",
            order_ref=order.id,
            subject_ref=f"dispatch:{order.project_arm}",
            data={
                "observation_type": ObservationType.PROCESS.value,
                "result": {
                    "project_id": order.project_id,
                    "project_root": str(project_workspace),
                    "adapter_id": adapter.id,
                    "argv": command,
                    "exit_code": completed.returncode,
                    "stdout": completed.stdout,
                    "stderr": completed.stderr,
                    "result_path": str(result_path),
                    "usage_path": str(usage_path),
                    "network_policy": sarcophagus.policy.network.value,
                },
            },
        )
        grapher.write_record(observation)

        agent_records = self.result_channel.read(result_path)
        for record in agent_records:
            if record.order_ref is None:
                record.order_ref = order.id
            elif record.order_ref != order.id:
                raise ValueError(f"agent result references wrong order: {record.order_ref}")
            grapher.write_record(record)

        usage_id = self._record_usage_if_reported(usage_path, order, adapter.id)
        if usage_id is None:
            report = adapter.usage_from_output(completed.stdout)
            if report is not None:
                usage_id = self._record_usage_report(report, order, adapter.id, source="structured_stdout")
        return DispatchResult(
            order_id=order.id,
            project_arm=order.project_arm,
            adapter_id=adapter.id,
            exit_code=completed.returncode,
            stdout=completed.stdout,
            stderr=completed.stderr,
            observation_id=observation.id,
            project_id=order.project_id,
            agent_record_ids=tuple(record.id for record in agent_records),
            usage_id=usage_id,
        )

    def _record_usage_if_reported(self, usage_path: Path, order: Order, adapter_id: str) -> str | None:
        if not usage_path.is_file():
            return None
        try:
            report = json.loads(usage_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise ValueError(f"invalid adapter usage report {usage_path}: {exc}") from exc
        return self._record_usage_report(report, order, adapter_id, source="adapter_report")

    def _record_usage_report(
        self,
        report: dict[str, object],
        order: Order,
        adapter_id: str,
        *,
        source: str,
    ) -> str:
        try:
            input_tokens = int(report["input_tokens"])
            output_tokens = int(report["output_tokens"])
        except (KeyError, TypeError, ValueError) as exc:
            raise ValueError(f"invalid adapter usage report: {exc}") from exc
        config = load_config(self.control_workspace)
        usage = TokenUsage.create(
            agent_id=str(report.get("agent_id") or adapter_id),
            agent_role="minion",
            project_id=str(
                report.get("project_id")
                or order.project_id
                or config.get("active_project")
                or config.get("project_id")
                or self.control_workspace.name
            ),
            task_id=order.id,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cached_tokens=int(report.get("cached_tokens") or 0),
            reasoning_tokens=int(report.get("reasoning_tokens") or 0),
            provider=str(report.get("provider")) if report.get("provider") else None,
            model=str(report.get("model")) if report.get("model") else None,
            source=source,
        )
        TokenUsageLedger(self.control_workspace).record(usage)
        return usage.id
