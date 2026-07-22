"""Tests for the decklist text parser."""

from lotrautofill.library.decklist import parse_decklist_text


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
