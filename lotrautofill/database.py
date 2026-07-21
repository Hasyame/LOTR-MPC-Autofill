"""Index the card library into a database.

Scans ``sets_folder`` for every set and chapter and records what is present:
sets -> chapters -> categories -> cards (number, name, double-sided, quantity),
plus per-unit counts. The result is a JSON-serialisable dict a UI can render.

**Missing cards.** A reliable per-card "missing" list can't be derived from the
folder structure alone: within a pack every category shares one number sequence
and each folder holds a non-contiguous slice, so numbering gaps flag other
folders' cards rather than absent ones. RingsDB only lists player-side cards, so
it can't verify encounter cards either. We therefore surface the one reliable
signal — ``cardlist.txt`` entries that matched no image — as a review list, and
leave authoritative missing-card detection to a future RingsDB player-card
cross-reference.
"""

from __future__ import annotations

import time
from pathlib import Path

from .build import BuildOptions, build
from .sets import discover_chapters, discover_sets


def build_database(root: Path) -> dict:
    root = Path(root).resolve()
    db = {
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "root": str(root),
        "sets": [],
    }
    options = BuildOptions(interactive=False)
    for set_folder in discover_sets(root):
        db["sets"].append(_scan_set(set_folder, root, options))
    return db


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
        cards.append({
            "number": e.number, "name": e.name, "category": e.category,
            "quantity": e.quantity, "double_sided": e.double_sided,
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


def _rel(folder: Path, root: Path) -> str:
    try:
        return str(folder.relative_to(root))
    except ValueError:
        return str(folder)
