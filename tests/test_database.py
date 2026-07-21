"""Tests for the card-library database index."""

from pathlib import Path

from lotrautofill.database import build_database


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
