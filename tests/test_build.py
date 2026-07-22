"""Integration tests for the folder -> manifest build (non-interactive)."""

from pathlib import Path

from lotrautofill.library.build import BuildOptions, build


def _touch(folder: Path, *names: str) -> None:
    folder.mkdir(parents=True, exist_ok=True)
    for n in names:
        (folder / n).write_bytes(b"")


def _setup(tmp: Path) -> Path:
    root = tmp / "Set" / "Set"

    # Card backs
    backs = tmp / "Card_Backs" / "Card_Backs"
    _touch(backs, "Encounter Card Back.jpg", "Player Card Back.jpg")

    # Encounter: cardlist quantities + an errata duplicate + an unlisted card
    enc = root / "Encounter" / "Pit"
    _touch(enc, "042 - Great Cave-troll.jpg", "043 - Orc Drummer.jpg",
           "043 - Orc Drummer (errata).jpg", "044 - Stray Goblin.jpg")
    (enc / "cardlist.txt").write_text(
        "2 Great Cave-troll\n1 Orc Drummer\n", encoding="utf-8"
    )

    # Nightmare: same-number front/back pair + an orphan B side
    nm = root / "Nightmare" / "Pit"
    _touch(nm, "001 - Flight.jpg", "001 - Setup.jpg", "002 - 2B - Pursued.jpg")
    (nm / "cardlist.txt").write_text("", encoding="utf-8")

    # Player: no cardlist, 1 copy each
    _touch(root / "Player", "001 - Bilbo.jpg")

    # Quest: A/B pair
    _touch(root / "Quest", "023 - 1A - Party.jpg", "023 - 1B - Party.jpg")

    return root


def _by_name(report):
    return {e.name: e for e in report.entries}


def test_build_pairs_and_quantities(tmp_path):
    root = _setup(tmp_path)
    report = build(root, BuildOptions(interactive=False))
    cards = _by_name(report)

    # Cardlist quantity applied.
    assert cards["Great Cave-troll"].quantity == 2
    assert not cards["Great Cave-troll"].double_sided

    # Errata collapsed to a single Orc Drummer using the errata version.
    assert cards["Orc Drummer"].quantity == 1
    assert "(errata)" in cards["Orc Drummer"].front.name

    # Unlisted encounter card auto-included at 1.
    assert cards["Stray Goblin"].quantity == 1
    assert len(report.auto_included) == 1

    # Same-number Nightmare pair became one double-sided card.
    assert cards["Flight"].double_sided
    assert cards["Flight"].back.name == "001 - Setup.jpg"

    # Orphan B side flagged and given the common (encounter) back by default.
    assert len(report.orphans) == 1

    # Quest A/B pair.
    assert cards["Party"].double_sided
    assert cards["Party"].back.name == "023 - 1B - Party.jpg"

    # Player: 1 copy, player back.
    assert cards["Bilbo"].quantity == 1
    assert cards["Bilbo"].back.name == "Player Card Back.jpg"


def test_errata_skip_policy(tmp_path):
    root = _setup(tmp_path)
    report = build(root, BuildOptions(interactive=False, errata="skip"))
    orc = _by_name(report)["Orc Drummer"]
    assert "(errata)" not in orc.front.name


def test_cardlist_front_slash_back_pairs_separate_images(tmp_path):
    root = tmp_path / "Set" / "Set"
    _touch(tmp_path / "Card_Backs" / "Card_Backs",
           "Encounter Card Back.jpg", "Player Card Back.jpg")
    enc = root / "Encounter" / "X"
    # A two-sided card whose sides are separate images with DIFFERENT numbers.
    _touch(enc, "011 - Daybreak.jpg", "012 - Nightfall.jpg")
    (enc / "cardlist.txt").write_text("2 Nightfall/Daybreak\n", encoding="utf-8")

    report = build(root, BuildOptions(interactive=False))
    # Resolved into ONE double-sided card at the cardlist quantity, not two
    # singles, and nothing left unmatched.
    ds = [e for e in report.entries if e.double_sided]
    assert len(ds) == 1
    assert ds[0].quantity == 2
    assert ds[0].front.name == "012 - Nightfall.jpg"
    assert ds[0].back.name == "011 - Daybreak.jpg"
    assert report.unmatched_cardlist == []
    assert len([e for e in report.entries if not e.double_sided]) == 0


def test_cardlist_pairs_front_with_no_number_shared_back(tmp_path):
    root = tmp_path / "Set" / "Set"
    _touch(tmp_path / "Card_Backs" / "Card_Backs",
           "Encounter Card Back.jpg", "Player Card Back.jpg")
    enc = root / "Encounter" / "X"
    # Two fronts share one back stored WITHOUT a number prefix.
    _touch(enc, "002 - Desecrated Ruins.jpg", "004 - Cursed Temple.jpg",
           "Edge of the Temple.jpg")
    (enc / "cardlist.txt").write_text(
        "1 Desecrated Ruins/Edge of the Temple\n"
        "1 Cursed Temple/Edge of the Temple\n", encoding="utf-8")

    report = build(root, BuildOptions(interactive=False))
    ds = [e for e in report.entries if e.double_sided]
    assert len(ds) == 2
    assert all(e.back.name == "Edge of the Temple.jpg" for e in ds)
    assert report.unmatched_cardlist == []


def test_same_number_even_count_pairs_into_couples(tmp_path):
    root = tmp_path / "Set" / "Set"
    _touch(tmp_path / "Card_Backs" / "Card_Backs",
           "Encounter Card Back.jpg", "Player Card Back.jpg")
    enc = root / "Encounter" / "X"
    # Number 0001 has 4 differently-named images -> two double-sided couples.
    _touch(enc, "0001 - Alpha.jpg", "0001 - Beta.jpg",
           "0001 - Gamma.jpg", "0001 - Delta.jpg")
    (enc / "cardlist.txt").write_text("", encoding="utf-8")

    report = build(root, BuildOptions(interactive=False))
    pairs = [e for e in report.entries if e.double_sided]
    assert len(pairs) == 2
    # Consecutive couples in sorted file order: (Alpha,Beta), (Delta,Gamma).
    couples = {(e.front.name, e.back.name) for e in pairs}
    assert ("0001 - Alpha.jpg", "0001 - Beta.jpg") in couples
    assert ("0001 - Delta.jpg", "0001 - Gamma.jpg") in couples
    assert len(report.orphans) == 0
