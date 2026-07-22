"""The canonical LOTR LCG product hierarchy (authored, not scraped).

Real-world buying philosophy drives the print units: an **EXPANSION** (deluxe
box) is bought whole and holds 3 scenarios; an **Adventure Pack** is bought
individually and holds 1 scenario. So a cycle is one or two expansions plus a
group of six adventure packs; a SAGA is only expansions.

Each product maps to a local set folder by name (accents/``The``/``Saga``
differences are absorbed by ``normalize``). Expansion scenario names are listed
here for display; adventure-pack scenarios are read from ``epiccardlist.txt``.
"""

from __future__ import annotations

EXPANSION = "EXPANSION"
AP_GROUP = "AP_GROUP"

# (cycle number, [(product name, kind, expansion scenarios)])
CYCLES: list[tuple[int, list[tuple[str, str, list[str]]]]] = [
    (1, [
        ("Core Set", EXPANSION,
         ["Passage Through Mirkwood", "Journey Along the Anduin",
          "Escape from Dol Guldur"]),
        ("Two-Player Limited Edition Starter", EXPANSION,
         ["The Oath", "The Caves of Nibin-Dûm"]),
        ("Shadows of Mirkwood", AP_GROUP, []),
    ]),
    (2, [
        ("Khazad-dûm", EXPANSION,
         ["Into the Pit", "The Seventh Level", "Flight from Moria"]),
        ("Dwarrowdelf", AP_GROUP, []),
    ]),
    (3, [
        ("Heirs of Númenor", EXPANSION,
         ["Peril in Pelargir", "Into Ithilien", "The Siege of Cair Andros"]),
        ("Against the Shadow", AP_GROUP, []),
    ]),
    (4, [
        ("The Voice of Isengard", EXPANSION,
         ["The Fords of Isen", "To Catch an Orc", "Into Fangorn"]),
        ("The Ring-maker", AP_GROUP, []),
    ]),
    (5, [
        ("The Lost Realm", EXPANSION,
         ["Intruders in Chetwood", "The Weather Hills", "Deadmen's Dike"]),
        ("Angmar Awakened", AP_GROUP, []),
    ]),
    (6, [
        ("The Grey Havens", EXPANSION,
         ["Voyage Across Belegaer", "The Fate of Númenor",
          "Raid on the Grey Havens"]),
        ("Dream-chaser", AP_GROUP, []),
    ]),
    (7, [
        ("The Sands of Harad", EXPANSION,
         ["Escape from Umbar", "Desert Crossing", "The Long Arm of Mordor"]),
        ("Haradrim", AP_GROUP, []),
    ]),
    (8, [
        ("The Wilds of Rhovanion", EXPANSION,
         ["Journey Up the Anduin", "Lost in Mirkwood", "The King's Quest"]),
        ("Ered Mithrin", AP_GROUP, []),
    ]),
    (9, [
        ("A Shadow in the East", EXPANSION,
         ["The River Running", "Danger in Dorwinion", "The Temple of Doom"]),
        ("Vengeance of Mordor", AP_GROUP, []),
    ]),
]

# (saga name, local folder name, [(expansion name, [scenarios])]) — sagas are
# a single local folder whose sub-folders are the expansions.
SAGAS: list[tuple[str, str, list[tuple[str, list[str]]]]] = [
    ("The Lord of the Rings", "The Lord of the Rings Saga", [
        ("The Black Riders",
         ["A Shadow of the Past", "A Knife in the Dark", "Flight to the Ford"]),
        ("The Road Darkens",
         ["The Ring Goes South", "Journey in the Dark", "Breaking of the Fellowship"]),
        ("The Treason of Saruman",
         ["The Uruk-hai", "Helm's Deep", "The Road to Isengard"]),
        ("The Land of Shadow",
         ["The Passage of the Marshes", "Journey to the Cross-roads", "Shelob's Lair"]),
        ("The Flame of the West",
         ["The Passing of the Grey Company", "The Siege of Gondor",
          "The Battle of the Pelennor Fields"]),
        ("The Mountain of Fire",
         ["The Tower of Cirith Ungol", "The Black Gate Opens", "Mount Doom"]),
    ]),
    ("The Hobbit", "The Hobbit Saga", [
        ("The Hobbit: Over Hill and Under Hill",
         ["We Must Away, Ere Break of Day", "Over the Misty Mountains Grim",
          "Dungeons Deep and Caverns Dim"]),
        ("The Hobbit: On the Doorstep",
         ["Flies and Spiders", "The Lonely Mountain", "The Battle of Five Armies"]),
    ]),
]
