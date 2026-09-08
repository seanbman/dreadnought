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
        "version": 2,
        "project_id": workspace.name,
        "active_project": None,
        "projects": {},
        "project_policies": {},
        "primary_agent": None,
        "agents": {},
        "ui": {"interactive_menu": True},
        "token_usage": {"enabled": True},
        "kernel": {"primary_isolation": True, "minion_channel": "control_plane"},
    }


def _kernelize_agent(agent_type: str, raw: dict[str, Any]) -> dict[str, Any]:
    data = dict(raw)
    executable = str(data.get("executable") or DEFAULT_AGENT_EXECUTABLES.get(agent_type) or agent_type).strip()
    args = list(data.get("args") or [])
    if data.get("provider_executable"):
        provider_executable = str(data["provider_executable"])
        provider_args = list(data.get("provider_args") or [])
    elif executable == "dreadnought" and args[:3] == ["kernel", "launch", "--agent-type"]:
        provider_executable = str(data.get("provider_executable") or DEFAULT_AGENT_EXECUTABLES.get(agent_type) or agent_type)
        provider_args = list(data.get("provider_args") or [])
    else:
        provider_executable = executable
        provider_args = args
    return {
        "type": agent_type,
        "executable": "dreadnought",
        "args": ["kernel", "launch", "--agent-type", agent_type],
        "provider_executable": provider_executable,
        "provider_args": provider_args,
        "kernel": "primary",
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
    raw_agents = dict(data.get("agents") or {})
    base["agents"] = {
        str(agent_type): _kernelize_agent(str(agent_type), dict(agent or {}))
        for agent_type, agent in raw_agents.items()
    }
    base["projects"] = dict(data.get("projects") or {})
    base["project_policies"] = dict(data.get("project_policies") or {})
    base["kernel"] = {**default_config(workspace)["kernel"], **dict(data.get("kernel") or {})}
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
    provider_executable = (executable or DEFAULT_AGENT_EXECUTABLES.get(agent_type) or agent_type).strip()
    if not provider_executable:
        raise ValueError("agent executable must not be empty")
    config = load_config(workspace)
    config.setdefault("agents", {})[agent_type] = _kernelize_agent(
        agent_type,
        {
            "type": agent_type,
            "executable": provider_executable,
            "args": list(args or []),
        },
    )
    if primary or not config.get("primary_agent"):
        config["primary_agent"] = agent_type
    save_config(workspace, config)
    return config
