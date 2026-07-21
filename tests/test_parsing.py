from pathlib import Path

from lotrautofill.library.parsing import parse_filename


def _parse(name: str):
    return parse_filename(Path(name))


def test_simple_card():
    c = _parse("042 - Great Cave-troll.jpg")
    assert c.number == "042"
    assert c.name == "Great Cave-troll"
    assert not c.is_errata
    assert c.side is None


def test_errata_card():
    c = _parse("003 - Nori (errata).jpg")
    assert c.number == "003"
    assert c.name == "Nori"
    assert c.is_errata


def test_apostrophe_placeholder_kept_in_name():
    c = _parse("013 - Thror_s Map.jpg")
    assert c.name == "Thror_s Map"


def test_quest_front_and_back():
    a = _parse("023 - 1A - An Unexpected Party.jpg")
    b = _parse("023 - 1B - An Unexpected Party.jpg")
    assert (a.stage, a.side) == ("1", "A")
    assert (b.stage, b.side) == ("1", "B")
    assert a.name == b.name == "An Unexpected Party"


def test_name_with_internal_dash():
    c = _parse("015 - Foe-hammer.jpg")
    assert c.name == "Foe-hammer"


def test_non_card_file_returns_none():
    assert _parse("readme.txt") is None
