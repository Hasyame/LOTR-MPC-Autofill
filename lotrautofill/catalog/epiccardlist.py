"""Parse the ``epiccardlist.txt`` files that ship in each set folder.

These are the authoritative card lists (name, type and **how many copies**) for a
box. Two shapes exist:

* an **EXPANSION** (deluxe box: Core Set, Khazad-dûm, saga boxes…) — a flat list
  of every card in the box, e.g. ``Guard of the Citadel(Ally)3``, grouped by
  section markers ``Player Cards N`` / ``Encounter Cards N`` / ``Quest Cards N``;
* an **Adventure-Pack group** (e.g. Shadows of Mirkwood) — one block per pack:
  the pack title, its cards + section markers, then ``TOTAL CARDS N``.

``parse_epiccardlist`` returns one unit per box (title ``None``) or per pack
(title = the pack name), each with its cards and the file's stated totals.
"""

from __future__ import annotations

import re

# "Name(Type)Count" — the type is the last parenthesis before the trailing count,
# so names that themselves contain parentheses are handled.
_CARD = re.compile(r"^(.*?)\(([^()]+)\)(\d+)$")
_SUBTOTAL = re.compile(r"^(Player|Encounter|Quest)\s+Cards\s*(\d+)$", re.IGNORECASE)
_TOTAL = re.compile(r"^TOTAL\s+CARDS\s*(\d+)$", re.IGNORECASE)

# Card type (in the parens) -> which of the three sections it belongs to.
_PLAYER_TYPES = {"hero", "ally", "event", "attachment"}
_QUEST_TYPES = {"quest"}


def category_for(card_type: str) -> str:
    """Player / Encounter / Quest for a card type. Everything that isn't a
    player card or a quest card (enemies, locations, treacheries, objectives,
    ship cards, setup…) is an Encounter card."""
    t = card_type.strip().lower()
    if t in _PLAYER_TYPES:
        return "Player"
    if t in _QUEST_TYPES:
        return "Quest"
    return "Encounter"


def parse_epiccardlist(text: str) -> list[dict]:
    """Parse epiccardlist.txt text into a list of units.

    Each unit is ``{"title": str | None, "cards": [{name, type, count,
    category}], "totals": {"Player": n, "Encounter": n, "Quest": n,
    "total": n}}``. An expansion file yields a single unit (``title`` None); an
    AP-group file yields one unit per Adventure Pack.
    """
    units: list[dict] = []
    cur: dict | None = None

    def flush() -> None:
        nonlocal cur
        if cur and cur["cards"]:
            units.append(cur)
        cur = None

    def ensure() -> dict:
        nonlocal cur
        if cur is None:
            cur = {"title": None, "cards": [], "totals": {}}
        return cur

    for raw in text.splitlines():
        line = raw.strip()
        if not line:
            continue
        m = _CARD.match(line)
        if m:
            name, ctype, count = m.group(1).strip(), m.group(2).strip(), int(m.group(3))
            ensure()["cards"].append({"name": name, "type": ctype,
                                      "count": count, "category": category_for(ctype)})
            continue
        ms = _SUBTOTAL.match(line)
        if ms:
            ensure()["totals"][ms.group(1).capitalize()] = int(ms.group(2))
            continue
        mt = _TOTAL.match(line)
        if mt:
            ensure()["totals"]["total"] = int(mt.group(1))
            flush()                      # end of this Adventure-Pack block
            continue
        # A plain line that is neither a card nor a total is a pack title.
        flush()
        cur = {"title": line, "cards": [], "totals": {}}
    flush()
    return units
