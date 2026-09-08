from pathlib import Path

from dreadnought.order import Order
from dreadnought.project_cli import run_project_cli
from dreadnought.project_factory import create_project


def test_project_order_cli_persists_explicit_project_target(tmp_path: Path, capsys) -> None:
    workspace = tmp_path / "workspace"
    create_project(workspace, "Alpha", "Build alpha")
    create_project(workspace, "Beta", "Build beta")

    rc = run_project_cli([
        "order",
        "beta",
        "Implement beta change",
        "--doctrine",
        "doctrine-1",
        "--campaign",
        "campaign-1",
        "--operation",
        "operation-1",
        "--root",
        str(workspace),
    ])

    assert rc == 0
    path = Path(capsys.readouterr().out.strip())
    order = Order.read(path)
    assert order.project_id == "beta"
    assert order.objective == "Implement beta change"
