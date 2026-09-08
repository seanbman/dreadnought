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
    agent = config["agents"]["codex"]
    assert agent["executable"] == "dreadnought"
    assert agent["args"] == ["kernel", "launch", "--agent-type", "codex"]
    assert agent["provider_executable"] == "codex"
    assert agent["provider_args"] == ["--model", "x"]


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
    assert stats["metering"]["complete"] is True
    assert stats["metering"]["unmetered_sessions"] == 0

    graph = load_graph(tmp_path / ".grapher" / "knowledge.json")
    notes = [node for node in graph["nodes"].values() if node.get("type") == "dreadnought_note"]
    assert notes
    assert "token_usage" in notes[-1]["content"]
    assert "task-1" in notes[-1]["content"]


def test_unmetered_primary_session_is_visible_in_stats(tmp_path: Path) -> None:
    ledger = TokenUsageLedger(tmp_path)
    ledger.record_unmetered_session(
        agent_id="codex",
        agent_role="primary",
        project_id="demo",
        exit_code=0,
    )

    stats = ledger.stats()
    assert stats["records"] == 0
    assert stats["total_tokens"] == 0
    assert stats["metering"]["complete"] is False
    assert stats["metering"]["unmetered_sessions"] == 1
    assert stats["metering"]["unmetered_by_role"]["primary"] == 1
    assert "provider-reported usage only" in stats["metering"]["note"]


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


def test_primary_cli_chat_records_unmetered_session(tmp_path: Path, monkeypatch) -> None:
    configure_agent(tmp_path, agent_type="codex", executable="codex", primary=True)
    monkeypatch.setattr("dreadnought.cli.subprocess.call", lambda command, cwd: 0)

    from dreadnought.cli import _launch_agent_chat

    assert _launch_agent_chat(tmp_path, "codex") == 0
    stats = TokenUsageLedger(tmp_path).stats()
    assert stats["metering"]["complete"] is False
    assert stats["metering"]["unmetered_sessions"] == 1
    assert stats["metering"]["unmetered_by_role"]["primary"] == 1
