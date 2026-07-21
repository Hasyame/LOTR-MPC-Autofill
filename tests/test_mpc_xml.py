"""Tests for mpc-autofill order.xml export."""

from xml.etree import ElementTree as ET

from lotrautofill.upload.plan import plan_from_manifest
from lotrautofill.upload.mpc_xml import plan_to_xml


def _plan(tmp):
    for n in ("g.jpg", "q_a.jpg", "q_b.jpg", "encback.jpg", "plyback.jpg"):
        (tmp / n).write_bytes(b"")
    manifest = {
        "root": str(tmp),
        "cards": [
            {"front": "g.jpg", "back": "encback.jpg", "quantity": 3,
             "name": "Goblin", "category": "Encounter"},
            {"front": "q_a.jpg", "back": "q_b.jpg", "quantity": 1,
             "name": "Quest", "category": "Quest", "double_sided": True},
            {"front": "plyc.jpg", "back": "plyback.jpg", "quantity": 1,
             "name": "Hero", "category": "Player"},
        ],
    }
    # plyc.jpg intentionally missing to exercise missing handling in plan.
    return plan_from_manifest(manifest)


def test_details_and_counts(tmp_path):
    xml = ET.fromstring(plan_to_xml(_plan(tmp_path), stock="(S33) Superior Smooth"))
    assert xml.findtext("details/quantity") == "5"      # 3 + 1 + 1
    assert xml.findtext("details/stock") == "(S33) Superior Smooth"
    assert xml.findtext("details/foil") == "false"


def test_front_slot_grouping(tmp_path):
    xml = ET.fromstring(plan_to_xml(_plan(tmp_path)))
    fronts = {c.findtext("name"): c.findtext("slots") for c in xml.iter("card")
              if c in list(xml.find("fronts"))}
    assert fronts["g.jpg"] == "0,1,2"       # 3 copies -> slots 0,1,2


def test_cardback_is_most_common(tmp_path):
    xml = ET.fromstring(plan_to_xml(_plan(tmp_path)))
    # Encounter back appears 3x (most common) -> becomes <cardback>.
    assert xml.findtext("cardback").endswith("encback.jpg")
    # The quest back and player back appear in <backs>, not as cardback.
    back_names = [c.findtext("name") for c in xml.find("backs").iter("card")]
    assert "q_b.jpg" in back_names
    assert "plyback.jpg" in back_names


def test_invalid_stock_rejected(tmp_path):
    try:
        plan_to_xml(_plan(tmp_path), stock="Nonsense")
    except ValueError:
        return
    raise AssertionError("expected ValueError for bad cardstock")
