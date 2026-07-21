"""Tests for the card-library database index."""

from pathlib import Path

from lotrautofill.catalog.database import _HobRef, _cross_reference, build_database


def test_hobref_matches_scenario_then_cycle():
    ref = {"scenarios": [
        {"cycle": "Shadows of Mirkwood", "name": "Conflict at the Carrock",
         "cards": {"Louis": {"normal": 1, "nightmare": 1}}},
        {"cycle": "Core Set", "name": "Passage Through Mirkwood",
         "cards": {"Forest Spider": {"normal": 4, "nightmare": 1}}},
    ]}
    h = _HobRef(ref)
    assert h.available
    # chapter name matches a scenario (number prefix stripped)
    assert "Louis" in h.cards_for("02 - Shadows of Mirkwood",
                                  "02 - Conflict at the Carrock")
    # a no-chapter set falls back to the cycle union
    assert "Forest Spider" in h.cards_for("01 - Core Set", "01 - Core Set")
    assert h.cards_for("99 - Unknown", "99 - Unknown") is None


def test_cross_reference_reports_missing():
    from lotrautofill.library.matching import normalize
    hob = {"Louis": {"normal": 1, "nightmare": 1},
           "Bert": {"normal": 1, "nightmare": 0},
           "NightmareOnly": {"normal": 0, "nightmare": 2},
           "Great Cave-troll (Enemy)": {"normal": 2, "nightmare": 2}}
    present = {normalize("Louis"): "Louis",
               normalize("Great Cave-troll"): "Great Cave-troll"}
    expected, missing = _cross_reference(hob, present)
    assert expected == 4
    assert "Bert" in missing and "NightmareOnly" in missing
    assert "Louis" not in missing
    # Type suffix stripped -> matches the local "Great Cave-troll".
    assert "Great Cave-troll (Enemy)" not in missing


def _touch(folder: Path, *names: str) -> None:
    folder.mkdir(parents=True, exist_ok=True)
    for n in names:
        (folder / n).write_bytes(b"")


def _library(tmp: Path) -> Path:
    root = tmp / "sets_folder"
    _touch(root / "Card_Backs" / "Card_Backs",
           "Encounter Card Back.jpg", "Player Card Back.jpg")

    # A plain box with one encounter card missing from disk.
    box = root / "03 - Box" / "03 - Box"
    _touch(box / "Encounter" / "E", "042 - Present.jpg")
    (box / "Encounter" / "E" / "cardlist.txt").write_text(
        "1 Present\n2 Absent Card\n", encoding="utf-8")
    _touch(box / "Player", "001 - Hero.jpg")
    return root


def test_database_catalogs_sets_and_review(tmp_path):
    db = build_database(_library(tmp_path))
    assert len(db["sets"]) == 1
    s = db["sets"][0]
    assert s["name"] == "03 - Box"
    assert not s["has_chapters"]
    assert s["cards_total"] >= 2                      # Present + Hero
    # The cardlist references "Absent Card" with no image -> review item.
    assert s["review_total"] == 1
    review = s["chapters"][0]["cardlist_review"]
    assert review[0]["name"] == "Absent Card"
    # by_category catalogs what is present.
    assert s["chapters"][0]["by_category"].get("Player") == 1
