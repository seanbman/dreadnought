from __future__ import annotations

from dataclasses import asdict
import json
import os
from pathlib import Path
import socket
import socketserver
from typing import Any

from .grapher import GrapherControlPlane
from .usage import TokenUsageLedger


CONTROL_SOCKET_ENV = "DREADNOUGHT_CONTROL_SOCKET"
PRIMARY_SCRATCH_ENV = "DREADNOUGHT_SCRATCH"


def _under(path: Path, root: Path) -> bool:
    try:
        path.resolve().relative_to(root.resolve())
    except ValueError:
        return False
    return True


class _BrokerServer(socketserver.ThreadingUnixStreamServer):
    daemon_threads = True

    def __init__(self, socket_path: str, handler, broker: "ControlPlaneBroker"):
        self.broker = broker
        super().__init__(socket_path, handler)


class _Handler(socketserver.StreamRequestHandler):
    def handle(self) -> None:
        raw = self.rfile.readline()
        try:
            request_data = json.loads(raw.decode("utf-8"))
            result = self.server.broker.dispatch(str(request_data.get("method") or ""), dict(request_data.get("params") or {}))
            payload = {"ok": True, "result": result}
        except Exception as exc:
            payload = {"ok": False, "error": str(exc)}
        self.wfile.write((json.dumps(payload, sort_keys=True) + "\n").encode("utf-8"))


class ControlPlaneBroker:
    """Host-side broker exposed to a kernel-isolated primary agent over a Unix socket."""

    def __init__(self, workspace: Path | str, scratch: Path | str):
        self.workspace = Path(workspace).resolve()
        self.scratch = Path(scratch).resolve()
        self.socket_path = self.scratch / "control.sock"
        self.server: _BrokerServer | None = None
        self.thread = None

    def __enter__(self) -> "ControlPlaneBroker":
        import threading

        self.scratch.mkdir(parents=True, exist_ok=True)
        if self.socket_path.exists():
            self.socket_path.unlink()
        self.server = _BrokerServer(str(self.socket_path), _Handler, self)
        self.thread = threading.Thread(target=self.server.serve_forever, name="dreadnought-control-broker", daemon=True)
        self.thread.start()
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        if self.server is not None:
            self.server.shutdown()
            self.server.server_close()
        if self.thread is not None:
            self.thread.join(timeout=2)
        if self.socket_path.exists():
            self.socket_path.unlink()

    def _allowed_order(self, value: str) -> Path:
        path = Path(value).resolve()
        canonical_orders = self.workspace / ".dreadnought" / "orders"
        if not (_under(path, self.scratch) or _under(path, canonical_orders)):
            raise ValueError("order path must live in primary scratch or .dreadnought/orders")
        return path

    def dispatch(self, method: str, params: dict[str, Any]) -> Any:
        if method == "grapher.query":
            plane = GrapherControlPlane(self.workspace, project_id=params.get("project_id"))
            return plane.query(str(params.get("text") or ""), limit=int(params.get("limit") or 10), mission=params.get("mission"))
        if method == "grapher.get":
            plane = GrapherControlPlane(self.workspace, project_id=params.get("project_id"))
            return plane.get(str(params.get("node_id") or ""))
        if method == "usage.stats":
            return TokenUsageLedger(self.workspace).stats(
                project_id=params.get("project_id"), task_id=params.get("task_id"), agent_role=params.get("agent_role")
            )
        if method == "minion.commission":
            from .minion import commission

            result = commission(
                self.workspace,
                self._allowed_order(str(params.get("order") or "")),
                mission_id=params.get("mission_id"),
                agent_type=params.get("agent_type"),
                scratch=self.scratch / "minions",
                timeout=int(params.get("timeout") or 300),
            )
            return asdict(result)
        raise ValueError(f"unsupported control-plane method: {method}")


def request(method: str, params: dict[str, Any] | None = None, *, socket_path: str | None = None) -> Any:
    target = socket_path or os.environ.get(CONTROL_SOCKET_ENV)
    if not target:
        raise RuntimeError("no Dreadnought control socket is available")
    payload = json.dumps({"method": method, "params": params or {}}, sort_keys=True) + "\n"
    with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as client:
        client.connect(target)
        client.sendall(payload.encode("utf-8"))
        chunks = b""
        while not chunks.endswith(b"\n"):
            part = client.recv(65536)
            if not part:
                break
            chunks += part
    response = json.loads(chunks.decode("utf-8"))
    if not response.get("ok"):
        raise RuntimeError(str(response.get("error") or "control-plane request failed"))
    return response.get("result")


def run_control_cli(argv: list[str]) -> int:
    import argparse

    parser = argparse.ArgumentParser(prog="dreadnought control", description="Kernel-safe primary-agent control-plane client")
    sub = parser.add_subparsers(dest="command", required=True)
    query = sub.add_parser("query")
    query.add_argument("text")
    query.add_argument("--project")
    query.add_argument("--mission")
    query.add_argument("--limit", type=int, default=10)
    get = sub.add_parser("get")
    get.add_argument("node_id")
    get.add_argument("--project")
    usage = sub.add_parser("usage")
    usage.add_argument("--project")
    usage.add_argument("--task")
    usage.add_argument("--role", choices=["primary", "minion"])
    commission = sub.add_parser("commission")
    commission.add_argument("order")
    commission.add_argument("--mission")
    commission.add_argument("--agent", choices=["codex", "cursor"])
    commission.add_argument("--timeout", type=int, default=300)
    args = parser.parse_args(argv)
    try:
        if args.command == "query":
            result = request("grapher.query", {"text": args.text, "project_id": args.project, "mission": args.mission, "limit": args.limit})
        elif args.command == "get":
            result = request("grapher.get", {"node_id": args.node_id, "project_id": args.project})
        elif args.command == "usage":
            result = request("usage.stats", {"project_id": args.project, "task_id": args.task, "agent_role": args.role})
        else:
            result = request("minion.commission", {"order": args.order, "mission_id": args.mission, "agent_type": args.agent, "timeout": args.timeout})
    except (OSError, ValueError, RuntimeError, json.JSONDecodeError) as exc:
        print(f"control request failed: {exc}")
        return 2
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0
