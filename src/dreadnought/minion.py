from __future__ import annotations

import argparse
from dataclasses import asdict
import json
from pathlib import Path
import tempfile

from .agent import configured_minion_adapter
from .config import load_config
from .dispatch import ProjectArmDispatcher
from .mission import Mission
from .order import Order


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
    if mission is not None and mission.capabilities.max_minions == 0:
        raise ValueError(
            "mission explicitly prohibits minion delegation (max_minions=0); "
            "only an operator-authored mission constraint may block commissioning"
        )

    selected = (agent_type or config.get("primary_agent") or "").strip()
    if not selected:
        raise ValueError("no agent is configured for minion commissioning")
    agent_config = (config.get("agents") or {}).get(selected)
    if not agent_config:
        raise ValueError(f"agent is not configured: {selected}")
    adapter = configured_minion_adapter(selected, executable=agent_config.get("executable"))

    order = Order.read(order_path.resolve())
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
