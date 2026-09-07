from __future__ import annotations

import json
from pathlib import Path

from grapher.store import load_graph

from dreadnought.agent import CommandAgentAdapter
from dreadnought.config import configure_agent, load_config
from dreadnought.grapher import GrapherControlPlane
from dreadnought.order import Order
from dreadnought.usage import TokenUsage, TokenUsageLedger


def test_agent_config_sets_primary(tmp_path: Path) -> None:
    configure_agent(tmp_path, agent_type="codex", executable="codex", args=["--model", "x"], primary=True)
    config = load_config(tmp_path)
    assert config["primary_agent"] == "codex"
    assert config["agents"]["codex"]["executable"] == "codex"
    assert config["agents"]["codex"]["args"] == ["--model", "x"]


def test_usage_aggregates_and_projects_into_grapher(tmp_path: Path) -> None:
    GrapherControlPlane(tmp_path).initialize()
    usage = TokenUsage.create(
        agent_id="agent:minion-1",
        agent_role="minion",
        project_id="demo",
        task_id="task-1",
        input_tokens=100,
        output_tokens=25,
        cached_tokens=10,
        reasoning_tokens=5,
        provider="example",
        model="model-a",
    )
    ledger = TokenUsageLedger(tmp_path)
    ledger.record(usage)

    stats = ledger.stats()
    assert stats["total_tokens"] == 125
    assert stats["by_role"]["minion"] == 125
    assert stats["by_project"]["demo"] == 125
    assert stats["by_task"]["task-1"] == 125

    graph = load_graph(tmp_path / ".grapher" / "knowledge.json")
    notes = [node for node in graph["nodes"].values() if node.get("type") == "dreadnought_note"]
    assert notes
    assert "token_usage" in notes[-1]["content"]
    assert "task-1" in notes[-1]["content"]


def test_command_adapter_exposes_usage_report_template(tmp_path: Path) -> None:
    order = Order.draft(
        doctrine_ref="doctrine-1",
        campaign_ref="campaign-1",
        operation_ref="operation-1",
        objective="test",
        project_arm="arm-1",
    )
    result_path = tmp_path / "results" / f"{order.id}.jsonl"
    adapter = CommandAgentAdapter(id="x", executable="agent", args=("--usage", "{usage}"))
    command = adapter.command(
        order=order,
        order_path=tmp_path / "order.json",
        result_path=result_path,
        scratch=tmp_path,
        workspace=tmp_path,
    )
    assert command[-1] == str(result_path.with_suffix(".usage.json"))
