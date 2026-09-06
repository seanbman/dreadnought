from pathlib import Path
import subprocess

from dreadnought.agent import CommandAgentAdapter
from dreadnought.dispatch import ProjectArmDispatcher
from dreadnought.order import Order


class FakeSarcophagus:
    def __init__(self) -> None:
        self.commands: list[list[str]] = []

    def run(self, command, *, timeout=300):
        self.commands.append(list(command))
        return subprocess.CompletedProcess(command, 0, stdout="agent-ok\n", stderr="")


class FakeGrapher:
    def __init__(self) -> None:
        self.records = []

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
        args=("--order", "{order}", "--arm", "{project_arm}", "literal"),
    )
    order_path = tmp_path / "order.json"
    command = adapter.command(order=order, order_path=order_path, scratch=tmp_path, workspace=tmp_path)
    assert command == ["agent-bin", "--order", str(order_path), "--arm", "arm-alpha", "literal"]


def test_dispatch_writes_order_packet_and_observer_record(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    scratch = tmp_path / "scratch"
    runner = FakeSarcophagus()
    graph = FakeGrapher()
    dispatcher = ProjectArmDispatcher(
        workspace=workspace,
        scratch=scratch,
        sarcophagus=runner,
        grapher=graph,
    )
    order = make_order()
    adapter = CommandAgentAdapter(id="fixture", executable="agent-bin", args=("{order}",))

    result = dispatcher.dispatch(order, adapter)

    packet = scratch / "orders" / f"{order.id}.json"
    assert packet.exists()
    assert runner.commands == [["agent-bin", str(packet)]]
    assert result.exit_code == 0
    assert result.stdout == "agent-ok\n"
    assert len(graph.records) == 1
    observation = graph.records[0]
    assert observation.actor_id == "dreadnought:observer"
    assert observation.order_ref == order.id
    assert observation.data["result"]["adapter_id"] == "fixture"
    assert observation.data["result"]["exit_code"] == 0


def test_invalid_order_is_not_dispatched(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    runner = FakeSarcophagus()
    graph = FakeGrapher()
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
