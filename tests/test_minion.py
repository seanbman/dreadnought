from pathlib import Path

import pytest

from dreadnought.agent import CodexMinionAdapter, CursorMinionAdapter
from dreadnought.config import configure_agent, load_config, save_config
from dreadnought.minion import commission
from dreadnought.mission import CapabilitySet, Mission
from dreadnought.order import Order


def _write_order(path: Path) -> Path:
    order = Order.draft(
        doctrine_ref="doctrine-1",
        campaign_ref="campaign-1",
        operation_ref="operation-1",
        objective="Inspect the bounded change and return testimony.",
    )
    order.write(path)
    return path


def _configure_mission(root: Path, max_minions: int | None) -> Mission:
    mission = Mission.draft("Commission a minion for bounded work.", str(root), "human:test")
    mission.objective = "Use a subordinate agent."
    mission.capabilities = CapabilitySet(max_minions=max_minions)
    path = root / ".dreadnought" / "missions" / f"{mission.id}.json"
    mission.write(path)
    configure_agent(root, agent_type="codex", executable="codex", primary=True)
    config = load_config(root)
    config["bootstrap_mission"] = mission.id
    save_config(root, config)
    return mission


def test_codex_minion_disables_unified_exec_inside_sarcophagus(tmp_path: Path) -> None:
    adapter = CodexMinionAdapter()
    order = Order.draft(
        doctrine_ref="doctrine-1",
        campaign_ref="campaign-1",
        operation_ref="operation-1",
        objective="Run bounded work.",
    )
    command = adapter.command(
        order=order,
        order_path=tmp_path / "order.json",
        result_path=tmp_path / "result.jsonl",
        scratch=tmp_path / "scratch",
        workspace=tmp_path,
    )
    assert "--dangerously-bypass-approvals-and-sandbox" in command
    idx = command.index("-c")
    assert command[idx + 1] == "features.unified_exec=false"


def test_codex_adapter_parses_turn_completed_usage() -> None:
    adapter = CodexMinionAdapter()
    report = adapter.usage_from_output(
        '{"type":"turn.started"}\n'
        '{"type":"turn.completed","usage":{"input_tokens":24763,"cached_input_tokens":24448,"output_tokens":122}}\n'
    )
    assert report == {
        "input_tokens": 24763,
        "output_tokens": 122,
        "cached_tokens": 24448,
        "reasoning_tokens": 0,
        "provider": "openai-codex-cli",
    }


def test_cursor_adapter_parses_result_usage() -> None:
    adapter = CursorMinionAdapter()
    report = adapter.usage_from_output(
        '{"type":"result","usage":{"inputTokens":120,"outputTokens":30,"cachedTokens":10}}\n'
    )
    assert report == {
        "input_tokens": 120,
        "output_tokens": 30,
        "cached_tokens": 10,
        "reasoning_tokens": 0,
        "provider": "cursor-cli",
    }


def test_explicit_zero_minions_blocks_commission(tmp_path: Path) -> None:
    _configure_mission(tmp_path, 0)
    order_path = _write_order(tmp_path / "order.json")

    with pytest.raises(ValueError, match="explicitly prohibits minion delegation"):
        commission(tmp_path, order_path)


def test_unspecified_minion_limit_allows_commission(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _configure_mission(tmp_path, None)
    order_path = _write_order(tmp_path / "order.json")
    seen = {}

    def fake_dispatch(self, order, adapter, *, timeout=300):
        seen["adapter"] = adapter
        seen["order"] = order
        return "commissioned"

    monkeypatch.setattr("dreadnought.minion.ProjectArmDispatcher.dispatch", fake_dispatch)
    result = commission(tmp_path, order_path)

    assert result == "commissioned"
    assert isinstance(seen["adapter"], CodexMinionAdapter)
