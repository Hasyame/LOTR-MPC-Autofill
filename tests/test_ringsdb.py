"""Network-free tests for the RingsDB deck import (parsing + resolution)."""

from lotrautofill import ringsdb
from lotrautofill.ringsdb import (
    decklist_id_from,
    parse_decklist_text,
    resolve_text_entries,
)


def test_parse_various_quantity_formats():
    text = "3x Gandalf\n2 Steward of Gondor\nSneak Attack x3\n"
    assert parse_decklist_text(text) == [
        (3, "Gandalf"), (2, "Steward of Gondor"), (3, "Sneak Attack"),
    ]


def test_parse_skips_headers_blanks_comments():
    text = "Heroes (3)\n\n# comment\n1x Aragorn\nAllies\n"
    assert parse_decklist_text(text) == [(1, "Aragorn")]


def test_parse_strips_trailing_pack():
    assert parse_decklist_text("2 Steward of Gondor (Core Set)\n") == [
        (2, "Steward of Gondor")
    ]


def test_decklist_id_from_plain_id():
    assert decklist_id_from("12345") == "12345"


def test_decklist_id_from_url():
    assert decklist_id_from("https://ringsdb.com/decklist/view/999/my-deck") == "999"


def test_decklist_id_from_non_match():
    assert decklist_id_from("mydeck.txt") is None


def test_resolve_exact_and_fuzzy():
    catalog = {
        "01001": {"code": "01001", "name": "Aragorn"},
        "01002": {"code": "01002", "name": "Sneak Attack"},
    }
    resolved, unmatched = resolve_text_entries(
        [(1, "Aragorn"), (2, "Sneak Atack"), (1, "Nonexistent Card")], catalog)
    assert not unmatched or unmatched[0]["name"] == "Nonexistent Card"
    by_name = {r.card["name"]: r for r in resolved}
    assert by_name["Aragorn"].match == "exact"
    assert by_name["Sneak Attack"].match == "fuzzy"


def test_clean_images_only_touches_image_dir(tmp_path):
    old = ringsdb.IMAGE_DIR
    try:
        img_dir = tmp_path / "imgs"
        img_dir.mkdir()
        inside = img_dir / "01001.png"
        inside.write_bytes(b"x")
        outside = tmp_path / "local_card.png"   # e.g. a toPrint image
        outside.write_bytes(b"x")

        ringsdb.IMAGE_DIR = img_dir
        removed = ringsdb.clean_images(referenced=[inside, outside])

        assert removed == 1
        assert not inside.exists()      # temp image deleted
        assert outside.exists()         # anything outside IMAGE_DIR is safe
    finally:
        ringsdb.IMAGE_DIR = old
