"""Regenerate the bundled card database from ``epiccardlist.txt`` files.

The card lists ship *with the program* so users only need to drop in card
images. This script rebuilds ``lotrautofill/catalog/data/cardlists.json`` from a
local library that still has the authoritative ``epiccardlist.txt`` files.

Usage:
    python scripts/build_carddb.py [LIBRARY_ROOT]

``LIBRARY_ROOT`` defaults to the usual ``sets_folder``. The output keys match
the product names in ``lotrautofill/catalog/hierarchy.py`` exactly.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from lotrautofill.catalog import hierarchy  # noqa: E402
from lotrautofill.catalog.epiccardlist import parse_epiccardlist  # noqa: E402
from lotrautofill.library.build import _load_cardlist  # noqa: E402
from lotrautofill.library.matching import normalize  # noqa: E402
from lotrautofill.library.model import CATEGORY_NIGHTMARE  # noqa: E402
from lotrautofill.library.parsing import image_folders_for_category  # noqa: E402
from lotrautofill.library.sets import (  # noqa: E402
    _has_direct_category, default_library_root, discover_chapters,
    discover_sets, display_name,
)

OUT = Path(__file__).resolve().parent.parent / \
    "lotrautofill" / "catalog" / "data" / "cardlists.json"


def _index(root: Path) -> dict:
    return {normalize(display_name(s.name)): s for s in discover_sets(root)}


def _find(name: str, index: dict):
    key = normalize(name)
    if key in index:
        return index[key]
    for k, v in index.items():          # tolerate "The"/"Saga" wording
        if key and (key in k or k in key):
            return v
    return None


def _read(folder: Path) -> list:
    f = folder / "epiccardlist.txt"
    if not f.is_file():
        return []
    return parse_epiccardlist(f.read_text(encoding="utf-8", errors="replace"))


def _cards(unit: dict) -> list:
    return [{"name": c["name"], "type": c["type"], "count": c["count"]}
            for c in unit["cards"]]


def _blocks(units: list) -> list:
    return [{"title": u["title"], "cards": _cards(u)} for u in units]


def _rel(p: Path, root: Path) -> str:
    return str(p.resolve().relative_to(root)).replace("\\", "/")


def _nightmare(root: Path) -> dict:
    """Nightmare cardlists keyed by unit id (folder path relative to root)."""
    out: dict = {}
    for nm in sorted(p for p in root.rglob("*")
                     if p.is_dir() and p.name == CATEGORY_NIGHTMARE):
        for f in image_folders_for_category(CATEGORY_NIGHTMARE, nm):
            cl = _load_cardlist(f)
            if cl:
                out[_rel(f, root)] = [{"name": n, "count": c} for c, n in cl]
    return out


def _standalone(root: Path, index: dict) -> dict:
    """Standalone-scenario Encounter cardlists, keyed by the Encounter folder id."""
    out: dict = {}
    for set_name in hierarchy.STANDALONE:
        folder = _find(set_name, index)
        if folder is None:
            continue
        chapters = discover_chapters(folder)
        scen_folders = chapters or [p for p in sorted(folder.rglob("*"))
                                    if p.is_dir() and _has_direct_category(p)][:1]
        for sf in scen_folders:
            cl = _load_cardlist(sf / "Encounter")
            if cl:
                out[_rel(sf / "Encounter", root)] = \
                    [{"name": n, "count": c} for c, n in cl]
    return out


def build(root: Path) -> dict:
    root = root.resolve()
    index = _index(root)
    db: dict = {"expansions": {}, "ap_groups": {}, "sagas": {},
                "nightmare": {}, "standalone": {}}
    for _n, products in hierarchy.CYCLES:
        for pname, kind, _scen in products:
            folder = _find(pname, index)
            if folder is None:
                print(f"  ! missing folder for {pname!r}")
                continue
            units = _read(folder)
            if kind == hierarchy.EXPANSION:
                db["expansions"][pname] = _cards(units[0]) if units else []
            else:
                db["ap_groups"][pname] = _blocks(units)
    for sname, folder_name, _exp in hierarchy.SAGAS:
        folder = _find(folder_name, index)
        db["sagas"][sname] = _blocks(_read(folder)) if folder else []
    db["nightmare"] = _nightmare(root)
    db["standalone"] = _standalone(root, index)
    return db


def main() -> int:
    root = Path(sys.argv[1]) if len(sys.argv) > 1 else default_library_root()
    print("Library root:", root)
    db = build(root)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(db, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"expansions: {len(db['expansions'])} "
          f"ap_groups: {len(db['ap_groups'])} sagas: {len(db['sagas'])} "
          f"nightmare: {len(db['nightmare'])} standalone: {len(db['standalone'])}")
    print("Wrote", OUT, f"({OUT.stat().st_size} bytes)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
