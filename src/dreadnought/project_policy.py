from __future__ import annotations

from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any

from .config import load_config, save_config


@dataclass(frozen=True)
class ProjectPolicy:
    max_minions: int | None = None
    primary_project_write: bool = False
    minion_channel: str = "control_plane"
    token_usage: bool = True

    def validate(self) -> None:
        if self.max_minions is not None and self.max_minions < 0:
            raise ValueError("max_minions must be >= 0 when supplied")
        if self.primary_project_write:
            raise ValueError("primary_project_write must remain false; primary agents cannot directly mutate projects")
        if self.minion_channel != "control_plane":
            raise ValueError("minion_channel must be control_plane")

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def project_policy(config: dict[str, Any], project_id: str) -> ProjectPolicy:
    raw = dict((config.get("project_policies") or {}).get(project_id) or {})
    policy = ProjectPolicy(
        max_minions=raw.get("max_minions"),
        primary_project_write=bool(raw.get("primary_project_write", False)),
        minion_channel=str(raw.get("minion_channel") or "control_plane"),
        token_usage=bool(raw.get("token_usage", True)),
    )
    policy.validate()
    return policy


def set_project_policy(workspace: Path | str, project_id: str, *, max_minions: int | None) -> ProjectPolicy:
    workspace = Path(workspace).resolve()
    policy = ProjectPolicy(max_minions=max_minions)
    policy.validate()
    config = load_config(workspace)
    policies = dict(config.get("project_policies") or {})
    policies[str(project_id)] = policy.to_dict()
    config["project_policies"] = policies
    save_config(workspace, config)
    return policy
