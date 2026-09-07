from __future__ import annotations

import json
from pathlib import Path
from typing import Any


DEFAULT_AGENT_EXECUTABLES = {
    "codex": "codex",
    "cursor": "agent",
}


def config_path(workspace: Path) -> Path:
    return workspace / ".dreadnought" / "config.json"


def default_config(workspace: Path) -> dict[str, Any]:
    return {
        "version": 1,
        "project_id": workspace.name,
        "primary_agent": None,
        "agents": {},
        "ui": {"interactive_menu": True},
        "token_usage": {"enabled": True},
    }


def load_config(workspace: Path) -> dict[str, Any]:
    path = config_path(workspace)
    if not path.is_file():
        return default_config(workspace)
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("Dreadnought config must be a JSON object")
    base = default_config(workspace)
    base.update(data)
    base["agents"] = dict(data.get("agents") or {})
    return base


def save_config(workspace: Path, config: dict[str, Any]) -> Path:
    path = config_path(workspace)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(config, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def configure_agent(
    workspace: Path,
    *,
    agent_type: str,
    executable: str | None = None,
    args: list[str] | None = None,
    primary: bool = False,
) -> dict[str, Any]:
    agent_type = agent_type.strip().lower()
    if not agent_type:
        raise ValueError("agent type must not be empty")
    executable = (executable or DEFAULT_AGENT_EXECUTABLES.get(agent_type) or agent_type).strip()
    if not executable:
        raise ValueError("agent executable must not be empty")
    config = load_config(workspace)
    config.setdefault("agents", {})[agent_type] = {
        "type": agent_type,
        "executable": executable,
        "args": list(args or []),
    }
    if primary or not config.get("primary_agent"):
        config["primary_agent"] = agent_type
    save_config(workspace, config)
    return config
