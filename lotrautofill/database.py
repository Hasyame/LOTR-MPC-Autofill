"""Index the card library into a database, with a Hall of Beorn cross-reference.

Scans ``sets_folder`` for every set and chapter and records what is present:
sets -> chapters -> categories -> cards (number, name, double-sided, quantity),
plus per-unit counts. The result is a JSON-serialisable dict a UI can render.

**Missing cards.** RingsDB only lists player-side cards, and folder numbering is
shared across categories, so neither gives a reliable per-card "missing" list.
Instead we cross-reference the **Hall of Beorn** scenario data (see
``hallofbeorn.py``): each local unit (chapter, or a set with no chapters) is
matched to a scenario (or a cycle's union of scenarios) by name, giving the true
expected card list — cards Hall of Beorn lists but that have no local image are
reported as missing. Also kept: ``cardlist.txt`` entries that matched no image.
"""

from __future__ import annotations

import re
import time
from pathlib import Path
from typing import Optional

from .build import BuildOptions, build
from .matching import best_match, normalize
from .parsing import parse_filename
from .sets import discover_chapters, discover_sets

_NUM_PREFIX = re.compile(r"^\d+\s*-\s*")
# Hall of Beorn appends a card's type in parens to disambiguate same-named cards.
_TYPE_SUFFIX = re.compile(
    r"\s*\((?:Enemy|Location|Treachery|Objective|Objective-[A-Za-z]+|Ally|Hero|"
    r"Attachment|Event|Quest|Setup|Ship-Enemy|Ship-Objective|Encounter Side Quest"
    r")\)\s*$", re.IGNORECASE)


def build_database(root: Path, hob_reference: Optional[dict] = None) -> dict:
    root = Path(root).resolve()
    if hob_reference is None:
        from .hallofbeorn import load_reference
        hob_reference = load_reference()
    hob = _HobRef(hob_reference)

    options = BuildOptions(interactive=False)
    sets = [_scan_set(set_folder, root, options) for set_folder in discover_sets(root)]

    # A card is "missing" only if it is absent from the ENTIRE local library:
    # shared encounter sets ship in one pack but are used by several scenarios.
    # Include double-sided backs so a side stored only as a back still counts.
    present: dict[str, str] = {}
    for s in sets:
        for ch in s["chapters"]:
            for c in ch["cards"]:
                present[normalize(c["name"])] = c["name"]
                if c.get("back"):
                    present[normalize(c["back"])] = c["back"]
    for s in sets:
        for ch in s["chapters"]:
            ch["expected_cards"], ch["missing"] = _cross_reference(
                hob.cards_for(s["name"], ch["name"]), present)
        s["missing_total"] = sum(len(ch["missing"]) for ch in s["chapters"])
        s["expected_total"] = sum(ch["expected_cards"] for ch in s["chapters"])

    return {
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "root": str(root),
        "has_reference": hob.available,
        "sets": sets,
    }


class _HobRef:
    """Hall of Beorn scenarios indexed by scenario name and by cycle."""

    def __init__(self, reference: Optional[dict]):
        self.by_scenario: dict[str, dict] = {}
        self.by_cycle: dict[str, dict] = {}
        self.available = bool(reference and reference.get("scenarios"))
        for s in (reference or {}).get("scenarios", []):
            self.by_scenario[normalize(s["name"])] = s["cards"]
            self.by_cycle.setdefault(normalize(s.get("cycle") or ""), {}).update(
                s["cards"])

    def cards_for(self, set_name: str, unit_name: str) -> Optional[dict]:
        key = normalize(_NUM_PREFIX.sub("", unit_name))
        if key in self.by_scenario:
            return self.by_scenario[key]
        ckey = normalize(_NUM_PREFIX.sub("", set_name))
        return self.by_cycle.get(ckey)


def _scan_set(set_folder: Path, root: Path, options: BuildOptions) -> dict:
    chapters = discover_chapters(set_folder)
    units = ([(c.name, c) for c in chapters] if chapters
             else [(set_folder.name, set_folder)])
    entry = {
        "name": set_folder.name,
        "has_chapters": bool(chapters),
        "chapters": [_scan_unit(label, folder, root, options)
                     for label, folder in units],
    }
    entry["cards_total"] = sum(c["unique_cards"] for c in entry["chapters"])
    entry["review_total"] = sum(len(c["cardlist_review"]) for c in entry["chapters"])
    return entry


def _scan_unit(label: str, folder: Path, root: Path, options: BuildOptions) -> dict:
    report = build(folder, options)
    by_category: dict[str, int] = {}
    cards: list[dict] = []
    for e in report.entries:
        by_category[e.category] = by_category.get(e.category, 0) + 1
        back_name = None
        if e.double_sided and e.back:
            pb = parse_filename(e.back)
            back_name = pb.name if pb else e.back.stem
        cards.append({
            "number": e.number, "name": e.name, "category": e.category,
            "quantity": e.quantity, "double_sided": e.double_sided,
            "back": back_name,
        })
    review = [{"name": u["name"], "quantity": u["quantity"], "source": u["source"]}
              for u in report.unmatched_cardlist]
    return {
        "name": label,
        "path": _rel(folder, root),
        "unique_cards": report.unique_cards,
        "total_slots": report.total_slots,
        "by_category": by_category,
        "orphans": len(report.orphans),
        "fuzzy_matches": len(report.fuzzy_matches),
        "cardlist_review": review,
        "cards": cards,
    }


def _cross_reference(hob_cards: Optional[dict], present: dict[str, str]
                     ) -> tuple[int, list[str]]:
    """Return (expected count, missing card names) vs Hall of Beorn.

    ``present`` maps normalized name -> display name for the WHOLE library, so
    shared encounter sets stored under another pack aren't flagged as missing.
    """
    if not hob_cards:
        return 0, []
    expected = 0
    missing: list[str] = []
    for name, q in hob_cards.items():
        if q.get("normal", 0) <= 0 and q.get("nightmare", 0) <= 0:
            continue
        expected += 1
        variants = _name_variants(name)
        if any(normalize(v) in present for v in variants):
            continue
        if any(best_match(v, present)[0] is not None for v in variants):
            continue
        missing.append(name)
    return expected, missing


_NIGHTMARE = re.compile(r"\s+Nightmare$", re.IGNORECASE)
_PAREN = re.compile(r"\s*\(([^)]+)\)\s*$")


def _name_variants(name: str) -> list[str]:
    """Alternate strings a Hall of Beorn card name may be stored under locally:
    the type-stripped base, the non-Nightmare base, and — for a branching card
    like "Search for an Exit (Blocked by Shadow)" — both the front part and the
    parenthetical side name."""
    variants = [name]
    base = _TYPE_SUFFIX.sub("", name)
    variants.append(base)
    variants.append(_NIGHTMARE.sub("", base))
    m = _PAREN.search(base)
    if m:
        variants.append(m.group(1))            # the branch / side name
        variants.append(base[:m.start()].strip())  # the part before the paren
    return [v for v in variants if v]


def _rel(folder: Path, root: Path) -> str:
    try:
        return str(folder.relative_to(root))
    except ValueError:
        return str(folder)
