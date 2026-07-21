"""Tests for the manifest -> upload plan step."""

from pathlib import Path

from lotrautofill.upload.plan import plan_from_manifest


def _manifest(tmp: Path) -> dict:
    # Create real files so existence checks pass.
    for n in ("front1.jpg", "front2.jpg", "encback.jpg", "questback.jpg"):
        (tmp / n).write_bytes(b"")
    return {
        "root": str(tmp),
        "cards": [
            {"front": "front1.jpg", "back": "encback.jpg", "quantity": 3,
             "name": "Goblin", "category": "Encounter"},
            {"front": "front2.jpg", "back": "questback.jpg", "quantity": 1,
             "name": "Quest", "category": "Quest", "double_sided": True},
        ],
    }


def test_quantities_expand_into_slots(tmp_path):
    plan = plan_from_manifest(_manifest(tmp_path))
    assert plan.total_cards == 4                # 3 + 1
    assert plan.slots[0].front.name == "front1.jpg"
    assert plan.slots[2].front.name == "front1.jpg"
    assert plan.slots[3].name == "Quest"


def test_unique_images_deduped_in_order(tmp_path):
    plan = plan_from_manifest(_manifest(tmp_path))
    assert [p.name for p in plan.unique_fronts] == ["front1.jpg", "front2.jpg"]
    assert [p.name for p in plan.unique_backs] == ["encback.jpg", "questback.jpg"]


def test_missing_files_reported(tmp_path):
    manifest = {
        "root": str(tmp_path),
        "cards": [{"front": "nope.jpg", "back": None, "quantity": 1,
                   "name": "X", "category": "Encounter"}],
    }
    plan = plan_from_manifest(manifest)
    assert len(plan.missing_files) == 1
