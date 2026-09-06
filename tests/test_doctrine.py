from pathlib import Path

from dreadnought.campaign import CampaignPlan, Operation
from dreadnought.doctrine import Doctrine
from dreadnought.order import Order


def test_doctrine_round_trip(tmp_path: Path):
    doctrine = Doctrine.draft("Improve responsive editor")
    doctrine.creative_authority = {"ui_layout": "high", "architecture": "low"}
    path = tmp_path / "doctrine.json"
    doctrine.write(path)

    loaded = Doctrine.read(path)
    assert loaded.objective == doctrine.objective
    assert loaded.validate() == []


def test_doctrine_rejects_unknown_agency_level():
    doctrine = Doctrine.draft("Test")
    doctrine.creative_authority = {"architecture": "unlimited"}
    assert doctrine.validate()


def test_campaign_requires_known_dependencies():
    campaign = CampaignPlan.draft("doctrine-1")
    campaign.operations.append(Operation(id="op-1", title="One", objective="Do one", dependencies=["op-2"]))
    assert "unknown operation" in campaign.validate()[0]


def test_order_preserves_project_arm_and_refs(tmp_path: Path):
    order = Order.draft(
        doctrine_ref="doctrine-1",
        campaign_ref="campaign-1",
        operation_ref="op-1",
        objective="Implement bounded change",
        project_arm="project-arm-ui",
    )
    path = tmp_path / "order.json"
    order.write(path)
    loaded = Order.read(path)
    assert loaded.project_arm == "project-arm-ui"
    assert loaded.validate() == []
