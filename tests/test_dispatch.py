from pathlib import Path
import subprocess

from grapher.store import load_graph

from dreadnought.agent import CommandAgentAdapter
from dreadnought.dispatch import ProjectArmDispatcher
from dreadnought.order import Order
from dreadnought.project_factory import create_project


class FakeSarcophagus:
    def __init__(self) -> None:
        self.commands: list[list[str]] = []

    def run(self, command, *, timeout=300):
        self.commands.append(list(command))
        return subprocess.CompletedProcess(command, 0, stdout="agent-ok\n", stderr="")


class FakeGrapher:
    def __init__(self) -> None:
        self.records = []
        self.project_root = Path(".").resolve()

    def write_record(self, record):
        self.records.append(record)


def make_order() -> Order:
    return Order.draft(
        doctrine_ref="doctrine-1",
        campaign_ref="campaign-1",
        operation_ref="operation-1",
        objective="Implement the bounded change",
        project_arm="arm-alpha",
    )


def test_command_adapter_renders_only_explicit_tokens(tmp_path: Path) -> None:
    order = make_order()
    adapter = CommandAgentAdapter(
        id="fixture",
        executable="agent-bin",
        args=("--order", "{order}", "--result", "{result}", "--arm", "{project_arm}", "literal"),
    )
    order_path = tmp_path / "order.json"
    result_path = tmp_path / "result.jsonl"
    command = adapter.command(
        order=order,
        order_path=order_path,
        result_path=result_path,
        scratch=tmp_path,
        workspace=tmp_path,
    )
    assert command == [
        "agent-bin",
        "--order",
        str(order_path),
        "--result",
        str(result_path),
        "--arm",
        "arm-alpha",
        "literal",
    ]


def test_dispatch_writes_order_packet_observation_and_evaluation(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    scratch = tmp_path / "scratch"
    runner = FakeSarcophagus()
    graph = FakeGrapher()
    graph.project_root = workspace
    dispatcher = ProjectArmDispatcher(
        workspace=workspace,
        scratch=scratch,
        sarcophagus=runner,
        grapher=graph,
    )
    order = make_order()
    adapter = CommandAgentAdapter(id="fixture", executable="agent-bin", args=("{order}", "{result}"))

    result = dispatcher.dispatch(order, adapter)

    packet = scratch / "orders" / f"{order.id}.json"
    result_path = scratch / "results" / f"{order.id}.jsonl"
    assert packet.exists()
    assert runner.commands == [["agent-bin", str(packet), str(result_path)]]
    assert result.exit_code == 0
    assert result.stdout == "agent-ok\n"
    assert result.agent_record_ids == ()
    assert result.accepted is True
    assert result.verification_status == "supported"
    assert len(result.verdict_ids) == 1
    assert len(graph.records) == 2
    observation = graph.records[0]
    verdict = graph.records[1]
    assert observation.actor_id == "dreadnought:observer"
    assert observation.order_ref == order.id
    assert observation.data["result"]["adapter_id"] == "fixture"
    assert observation.data["result"]["exit_code"] == 0
    assert observation.data["result"]["result_path"] == str(result_path)
    assert verdict.actor_id == "dreadnought:evaluator"
    assert verdict.subject_ref == order.id
    assert verdict.data["status"] == "supported"


def test_dispatch_routes_explicit_project_without_switching_workspace_default(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    create_project(workspace, "Alpha", "Build alpha")
    create_project(workspace, "Beta", "Build beta")
    scratch = tmp_path / "scratch"
    runner = FakeSarcophagus()
    dispatcher = ProjectArmDispatcher(workspace=workspace, scratch=scratch, sarcophagus=runner)
    order = make_order()
    order.project_id = "beta"
    adapter = CommandAgentAdapter(
        id="fixture",
        executable="agent-bin",
        args=("{workspace}", "{scratch}"),
    )

    result = dispatcher.dispatch(order, adapter)

    assert result.project_id == "beta"
    assert runner.commands == [["agent-bin", str(workspace / "beta"), str(scratch / "beta")]]
    packet = scratch / "beta" / "orders" / f"{order.id}.json"
    assert packet.is_file()
    beta = load_graph(workspace / "beta" / ".grapher" / "knowledge.json")
    alpha = load_graph(workspace / "alpha" / ".grapher" / "knowledge.json")
    assert result.observation_id in beta["nodes"]
    assert all(verdict_id in beta["nodes"] for verdict_id in result.verdict_ids)
    assert result.observation_id not in alpha["nodes"]


def test_invalid_order_is_not_dispatched(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    runner = FakeSarcophagus()
    graph = FakeGrapher()
    graph.project_root = workspace
    dispatcher = ProjectArmDispatcher(
        workspace=workspace,
        scratch=tmp_path / "scratch",
        sarcophagus=runner,
        grapher=graph,
    )
    order = make_order()
    order.objective = ""
    adapter = CommandAgentAdapter(id="fixture", executable="agent-bin")

    try:
        dispatcher.dispatch(order, adapter)
    except ValueError as exc:
        assert "invalid order" in str(exc)
    else:
        raise AssertionError("invalid order should fail dispatch")

    assert runner.commands == []
    assert graph.records == []
