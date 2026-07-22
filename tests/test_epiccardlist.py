"""Tests for the epiccardlist.txt parser."""

from lotrautofill.catalog.epiccardlist import category_for, parse_epiccardlist

EXPANSION = """\
Aragorn(Hero)1
Guard of the Citadel(Ally)3
Sneak Attack(Event)2
Steward of Gondor(Attachment)2
Player Cards8
Forest Spider(Enemy)4
Old Forest Road(Location)2
Encounter Cards6
Flies and Spiders(Quest)1
Quest Cards1
"""

AP_GROUP = """\
The Hunt for Gollum
Bilbo Baggins(Hero)1
Player Cards1
Hunters from Mordor(Enemy)5
Encounter Cards5
The Hunt Begins(Quest)1
Quest Cards1
TOTAL CARDS7

Conflict at the Carrock
Frodo Baggins(Hero)1
Player Cards1
Muck Adder(Enemy)4
Encounter Cards4
Flooded(Quest)1
Quest Cards1
TOTAL CARDS6
"""


def test_expansion_is_one_unit_with_copy_counts():
    units = parse_epiccardlist(EXPANSION)
    assert len(units) == 1
    u = units[0]
    assert u["title"] is None
    # Copies (not distinct lines): 1+3+2+2 player, 4+2 encounter, 1 quest.
    copies = {"Player": 0, "Encounter": 0, "Quest": 0}
    for c in u["cards"]:
        copies[c["category"]] += c["count"]
    assert copies == {"Player": 8, "Encounter": 6, "Quest": 1}
    assert u["totals"] == {"Player": 8, "Encounter": 6, "Quest": 1}


def test_ap_group_splits_into_one_unit_per_pack():
    units = parse_epiccardlist(AP_GROUP)
    assert [u["title"] for u in units] == ["The Hunt for Gollum", "Conflict at the Carrock"]
    assert units[0]["totals"]["total"] == 7
    assert units[1]["cards"][0] == {"name": "Frodo Baggins", "type": "Hero",
                                    "count": 1, "category": "Player"}


def test_card_name_with_parentheses():
    # The type is the LAST parenthesis before the count.
    u = parse_epiccardlist("A Chosen Path (Beorn's Path)(Quest)1\n")[0]
    c = u["cards"][0]
    assert c["name"] == "A Chosen Path (Beorn's Path)" and c["type"] == "Quest"


def test_category_mapping():
    assert category_for("Hero") == category_for("Ally") == "Player"
    assert category_for("Attachment") == category_for("Event") == "Player"
    assert category_for("Enemy") == category_for("Objective-Ally") == "Encounter"
    assert category_for("Location") == category_for("Treachery") == "Encounter"
    assert category_for("Quest") == "Quest"
