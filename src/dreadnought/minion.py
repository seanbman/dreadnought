from __future__ import annotations

import argparse
from dataclasses import asdict
import json
from pathlib import Path
import tempfile

from .agent import configured_minion_adapter
from .config import load_config
from .dispatch import ProjectArmDispatcher
from .limits import MinionSlotManager
from .mission import Mission
from .order import Order
from .project_policy import project_policy


def _mission_path(root: Path, mission_id: str) -> Path:
    name = mission_id if mission_id.endswith(".json") else f"{mission_id}.json"
    return root / ".dreadnought" / "missions" / name


def _resolve_mission(root: Path, requested: str | None) -> Mission | None:
    config = load_config(root)
    mission_id = requested or config.get("bootstrap_mission")
    if not mission_id:
        return None
    path = _mission_path(root, str(mission_id))
    if not path.is_file():
        raise ValueError(f"mission not found: {mission_id}")
    return Mission.read(path)


def _default_scratch(root: Path) -> Path:
    return Path(tempfile.gettempdir()) / "dreadnought" / root.name / "minions"


def _effective_limit(config: dict, mission: Mission | None, project_id: str) -> int | None:
    limits = []
    policy_limit = project_policy(config, project_id).max_minions
    if policy_limit is not None:
        limits.append(policy_limit)
    if mission is not None and mission.capabilities.max_minions is not None:
        limits.append(mission.capabilities.max_minions)
    return min(limits) if limits else None


def commission(
    root: Path,
    order_path: Path,
    *,
    mission_id: str | None = None,
    agent_type: str | None = None,
    scratch: Path | None = None,
    timeout: int = 300,
):
    root = root.resolve()
    config = load_config(root)
    mission = _resolve_mission(root, mission_id)
    order = Order.read(order_path.resolve())
    project_id = str(order.project_id or config.get("active_project") or config.get("project_id") or root.name)
    limit = _effective_limit(config, mission, project_id)
    if limit == 0:
        raise ValueError(
            "project or mission explicitly prohibits minion delegation (max_minions=0); "
            "only operator-authored project/mission policy may block commissioning"
        )

    selected = (agent_type or config.get("primary_agent") or "").strip()
    if not selected:
        raise ValueError("no agent is configured for minion commissioning")
    agent_config = (config.get("agents") or {}).get(selected)
    if not agent_config:
        raise ValueError(f"agent is not configured: {selected}")
    provider_executable = agent_config.get("provider_executable") or agent_config.get("executable")
    adapter = configured_minion_adapter(selected, executable=provider_executable)

    with MinionSlotManager(root).lease(project_id, limit):
        return ProjectArmDispatcher(
            workspace=root,
            scratch=(scratch or _default_scratch(root)).resolve(),
        ).dispatch(order, adapter, timeout=timeout)


def run_minion_cli(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(
        prog="dreadnought minion",
        description="Commission subordinate agents through Project Arm / Sarcophagus",
    )
    sub = parser.add_subparsers(dest="command", required=True)
    commission_parser = sub.add_parser("commission", help="commission one configured minion for an existing Order")
    commission_parser.add_argument("order", help="path to a Dreadnought Order JSON document")
    commission_parser.add_argument("--root", default=".")
    commission_parser.add_argument("--mission")
    commission_parser.add_argument("--agent", choices=["codex", "cursor"])
    commission_parser.add_argument("--scratch")
    commission_parser.add_argument("--timeout", type=int, default=300)
    args = parser.parse_args(argv)

    if args.command == "commission":
        try:
            result = commission(
                Path(args.root),
                Path(args.order),
                mission_id=args.mission,
                agent_type=args.agent,
                scratch=Path(args.scratch) if args.scratch else None,
                timeout=args.timeout,
            )
        except (OSError, ValueError, RuntimeError, json.JSONDecodeError) as exc:
            print(f"minion commission failed: {exc}")
            return 2
        print(json.dumps(asdict(result), indent=2))
        return 0 if result.exit_code == 0 else 1
    return 2
