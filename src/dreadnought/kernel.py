from __future__ import annotations

import argparse
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
from uuid import uuid4

from .config import load_config
from .control import CONTROL_SOCKET_ENV, PRIMARY_SCRATCH_ENV, ControlPlaneBroker
from .usage import TokenUsageLedger


_BASE_ENV = ("PATH", "LANG", "LC_ALL", "TERM", "HOME", "USER", "LOGNAME", "SHELL", "TMPDIR", "XDG_CONFIG_HOME")
_PROVIDER_ENV = {
    "codex": ("OPENAI_API_KEY", "CODEX_HOME"),
    "cursor": ("CURSOR_API_KEY",),
}
_BLOCKED_ENV = {
    "GITHUB_TOKEN", "GH_TOKEN", "SSH_AUTH_SOCK", "GIT_ASKPASS", "GIT_SSH_COMMAND",
    "DBUS_SESSION_BUS_ADDRESS", "AWS_ACCESS_KEY_ID", "AWS_SECRET_ACCESS_KEY",
}


class PrimaryKernel:
    """Launch the primary agent with the canonical workspace read-only.

    The agent receives writable scratch, a private writable /tmp, and a Unix-domain
    control socket. Canonical mutation and minion commissioning remain host-side
    Dreadnought operations. Provider-owned runtime state is selectively rebound
    writable when required.
    """

    def __init__(self, workspace: Path | str):
        self.workspace = Path(workspace).resolve()

    @staticmethod
    def _bubblewrap_probe(backend: str) -> tuple[bool, str | None]:
        """Verify that bubblewrap can actually create the user namespace it needs."""
        try:
            result = subprocess.run(
                [
                    backend,
                    "--unshare-user",
                    "--uid", "0",
                    "--gid", "0",
                    "--ro-bind", "/", "/",
                    "--tmpfs", "/tmp",
                    "--", "/bin/true",
                ],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.PIPE,
                text=True,
                timeout=5,
                check=False,
            )
        except (OSError, subprocess.TimeoutExpired) as exc:
            return False, str(exc)
        detail = (result.stderr or "").strip() or None
        return result.returncode == 0, detail

    def doctor(self) -> dict[str, object]:
        backend = shutil.which("bwrap")
        if backend is None:
            available = False
            detail = "bubblewrap executable not found"
        else:
            available, detail = self._bubblewrap_probe(backend)
        return {
            "backend": "bubblewrap",
            "available": available,
            "detail": detail,
            "canonical_workspace": "read_only",
            "minion_channel": "control_plane",
            "git_credentials_exposed": False,
            "private_tmp": True,
        }

    def _scratch(self) -> Path:
        return Path(tempfile.gettempdir()) / "dreadnought" / self.workspace.name / "primary" / uuid4().hex

    @staticmethod
    def _provider_env(agent_type: str) -> dict[str, str]:
        allowed = set(_BASE_ENV) | set(_PROVIDER_ENV.get(agent_type, ()))
        return {key: value for key, value in os.environ.items() if key in allowed and key not in _BLOCKED_ENV}

    @staticmethod
    def _provider_args(agent_type: str, args: list[str]) -> list[str]:
        """Avoid nesting a provider sandbox inside Dreadnought's outer kernel."""
        rendered = list(args)
        if agent_type != "codex":
            return rendered
        if "--dangerously-bypass-approvals-and-sandbox" in rendered:
            return rendered
        for index, arg in enumerate(rendered):
            if arg in {"--sandbox", "-s"}:
                if index + 1 >= len(rendered):
                    raise ValueError("Codex sandbox option requires a mode")
                mode = rendered[index + 1]
                if mode != "danger-full-access":
                    raise ValueError(
                        "Codex primary must use --sandbox danger-full-access inside Dreadnought's outer sandbox"
                    )
                return rendered
            if arg.startswith("--sandbox="):
                mode = arg.split("=", 1)[1]
                if mode != "danger-full-access":
                    raise ValueError(
                        "Codex primary must use --sandbox danger-full-access inside Dreadnought's outer sandbox"
                    )
                return rendered
        return ["--sandbox", "danger-full-access", *rendered]

    def _provider_writable_paths(self, agent_type: str, env: dict[str, str]) -> list[Path]:
        """Return narrowly scoped provider runtime paths that must remain writable."""
        if agent_type != "codex":
            return []

        home = Path(env.get("HOME") or Path.home()).expanduser().resolve()
        codex_home = Path(env.get("CODEX_HOME") or home / ".codex").expanduser().resolve()
        try:
            codex_home.relative_to(self.workspace)
        except ValueError:
            pass
        else:
            raise ValueError("CODEX_HOME must be outside the read-only canonical workspace")

        codex_home.mkdir(parents=True, exist_ok=True)
        env["CODEX_HOME"] = str(codex_home)
        return [codex_home]

    @staticmethod
    def _credential_masks() -> list[tuple[str, str]]:
        home = Path.home()
        masks: list[tuple[str, str]] = []
        for path in (home / ".ssh", home / ".config" / "gh"):
            if path.exists():
                masks.append(("dir", str(path)))
        for path in (home / ".gitconfig", home / ".git-credentials"):
            if path.exists():
                masks.append(("file", str(path)))
        return masks

    def run(self, *, agent_type: str, executable: str, args: list[str]) -> int:
        backend = shutil.which("bwrap")
        if backend is None:
            raise RuntimeError("bubblewrap is required for primary-agent kernel isolation; refusing unsandboxed launch")
        available, detail = self._bubblewrap_probe(backend)
        if not available:
            suffix = f": {detail}" if detail else ""
            raise RuntimeError(f"bubblewrap is installed but unusable for primary-agent isolation{suffix}")
        if not self.workspace.is_dir():
            raise ValueError(f"workspace does not exist: {self.workspace}")
        scratch = self._scratch()
        scratch.mkdir(parents=True, exist_ok=True)
        env = self._provider_env(agent_type)
        writable_paths = self._provider_writable_paths(agent_type, env)
        env["TMPDIR"] = "/tmp"

        with ControlPlaneBroker(self.workspace, scratch) as broker:
            env[CONTROL_SOCKET_ENV] = str(broker.socket_path)
            env[PRIMARY_SCRATCH_ENV] = str(scratch)
            env["DREADNOUGHT_KERNEL"] = "primary"
            argv = [
                backend,
                "--die-with-parent",
                "--new-session",
                "--proc", "/proc",
                "--dev", "/dev",
                "--ro-bind", "/", "/",
                "--tmpfs", "/tmp",
                "--ro-bind", str(self.workspace), str(self.workspace),
                "--bind", str(scratch), str(scratch),
                "--chdir", str(self.workspace),
            ]
            for path in writable_paths:
                argv.extend(("--bind", str(path), str(path)))
            for kind, path in self._credential_masks():
                if kind == "dir":
                    argv.extend(("--tmpfs", path))
                else:
                    argv.extend(("--ro-bind", "/dev/null", path))
            provider_args = self._provider_args(agent_type, args)
            argv.extend(("--", executable, *provider_args))
            return subprocess.call(argv, cwd=self.workspace, env=env)


def run_kernel_cli(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(prog="dreadnought kernel", description="Internal primary-agent kernel launcher")
    sub = parser.add_subparsers(dest="command", required=True)
    launch = sub.add_parser("launch")
    launch.add_argument("--agent-type", required=True)
    launch.add_argument("--root", default=".")
    args = parser.parse_args(argv)
    if args.command != "launch":
        return 2
    root = Path(args.root).resolve()
    config = load_config(root)
    agent = (config.get("agents") or {}).get(args.agent_type)
    if not agent:
        print(f"agent is not configured: {args.agent_type}", file=sys.stderr)
        return 2
    executable = str(agent.get("provider_executable") or "").strip()
    provider_args = list(agent.get("provider_args") or [])
    if not executable:
        print(f"agent provider executable is missing: {args.agent_type}", file=sys.stderr)
        return 2

    ledger = TokenUsageLedger(root)
    project_id = str(config.get("active_project") or config.get("project_id") or root.name)
    session_id = ledger.mark_active_session(
        agent_id=args.agent_type,
        agent_role="primary",
        project_id=project_id,
        source="kernel_primary_chat",
    )
    try:
        return PrimaryKernel(root).run(agent_type=args.agent_type, executable=executable, args=provider_args)
    except (OSError, ValueError, RuntimeError) as exc:
        print(f"primary kernel launch failed: {exc}", file=sys.stderr)
        return 2
    finally:
        ledger.clear_active_session(session_id)


if __name__ == "__main__":
    raise SystemExit(run_kernel_cli(sys.argv[1:]))
