"""Build the browse catalog from the authored hierarchy + the bundled card DB.

Cycle -> [Expansion(s) + Adventure-Pack group] -> printable "units" (a box or a
pack), matched to the local card images with the **copy counts** stated by the
bundled card database. A SAGA is a set of expansion units. Nightmare and
standalone scenarios are handled elsewhere.

The card lists ship *with the program* (``catalog/data/cardlists.json``): the
user only needs to drop in card images, not the ``epiccardlist.txt`` files.
"""

from __future__ import annotations

import json
import sys
from functools import lru_cache
from pathlib import Path

from ..library.build import BuildOptions, build
from ..library.matching import normalize
from ..library.sets import discover_chapters, discover_sets, display_name
from . import hierarchy


@lru_cache(maxsize=1)
def _load_db() -> dict:
    """The bundled card database (works both frozen and from source)."""
    meipass = getattr(sys, "_MEIPASS", None)
    base = Path(meipass) / "lotrautofill" / "catalog" / "data" if meipass \
        else Path(__file__).resolve().parent / "data"
    f = base / "cardlists.json"
    if not f.is_file():
        return {"expansions": {}, "ap_groups": {}, "sagas": {}}
    return json.loads(f.read_text(encoding="utf-8"))


def _norm_index(d: dict) -> dict:
    """A name->value view of a DB section, keyed by normalized name."""
    return {normalize(k): v for k, v in d.items()}


def _rel(p: Path, root: Path) -> str:
    try:
        return str(Path(p).resolve().relative_to(root)).replace("\\", "/")
    except ValueError:
        return str(p)


def _folder_index(root: Path) -> dict:
    return {normalize(display_name(s.name)): s for s in discover_sets(root)}


def _find_folder(name: str, index: dict):
    key = normalize(name)
    if key in index:
        return index[key]
    for k, v in index.items():          # tolerate "The"/"Saga" wording
        if key and (key in k or k in key):
            return v
    return None


def _match_unit(folder: Path, epic_cards: list, root: Path,
                set_name: str, chapter: str) -> dict:
    """Match one epiccardlist block to a folder's images. Returns present cards
    (with per-image copy quantity, and the set/chapter needed to resolve them
    for the print list), the missing names, and the copy total."""
    entries = [e for e in build(folder, BuildOptions(interactive=False)).entries
               if e.category != "Nightmare"]
    by_name: dict[str, list] = {}
    for e in entries:
        by_name.setdefault(normalize(e.name), []).append(e)

    epic_count: dict[str, int] = {}
    for c in epic_cards:
        epic_count[normalize(c["name"])] = epic_count.get(normalize(c["name"]), 0) + c["count"]

    cards, total = [], 0
    for nm, imgs in by_name.items():
        # epiccardlist copies spread over however many images share the name
        # (a player card = 1 image x N copies; a branching quest = N images x 1).
        count = epic_count.get(nm, len(imgs))
        qty = max(1, round(count / len(imgs)))
        for e in imgs:
            cards.append({"name": e.name, "front": _rel(e.front, root),
                          "category": e.category, "quantity": qty,
                          "set": set_name, "chapter": chapter})
            total += qty
    missing_by: dict[str, int] = {}
    for c in epic_cards:
        if normalize(c["name"]) not in by_name:
            missing_by[c["name"]] = missing_by.get(c["name"], 0) + c["count"]
    missing = [{"name": n, "count": q} for n, q in missing_by.items()]
    return {"cards": cards, "missing": missing, "cards_total": total}


def _leaf(units_cache: dict, folder: Path, epic_cards: list, root: Path,
          name: str, kind: str, scenarios: list,
          set_name: str, chapter: str) -> dict:
    """A printable box/pack node; stashes its cards + missing list by id."""
    m = _match_unit(folder, epic_cards, root, set_name, chapter)
    uid = _rel(folder, root)
    units_cache[uid] = {"cards": m["cards"], "missing": m["missing"]}
    return {"id": uid, "name": name, "kind": kind, "scenarios": scenarios,
            "cards_total": m["cards_total"], "missing_total": len(m["missing"]),
            "available": bool(m["cards"]) and m["cards_total"] > len(m["missing"])}


def _blocks_to_subfolders(set_folder: Path, epic_units: list) -> list:
    """Pair epiccardlist blocks (by title) with a set's scenario sub-folders."""
    subs = {normalize(display_name(c.name)): c for c in discover_chapters(set_folder)}
    out = []
    for u in epic_units:
        folder = subs.get(normalize(u["title"] or ""))
        if folder is not None:
            out.append((u, folder))
    return out


def build_catalog(root: Path) -> dict:
    """The full browse catalog: cycles + sagas, plus a ``units`` id->cards map."""
    root = Path(root).resolve()
    index = _folder_index(root)
    units_cache: dict[str, list] = {}

    db = _load_db()
    exp_db = _norm_index(db.get("expansions", {}))
    ap_db = _norm_index(db.get("ap_groups", {}))
    saga_db = _norm_index(db.get("sagas", {}))

    cycles = []
    for n, products in hierarchy.CYCLES:
        prods = []
        for pname, kind, scenarios in products:
            folder = _find_folder(pname, index)
            if folder is None:
                prods.append({"name": pname, "kind": kind, "available": False,
                              "cards_total": 0, "missing_total": 0})
                continue
            if kind == hierarchy.EXPANSION:
                block = exp_db.get(normalize(pname), [])
                prods.append(_leaf(units_cache, folder, block, root,
                                   pname, "EXPANSION", scenarios,
                                   folder.name, ""))
            else:  # AP_GROUP: one leaf per adventure pack
                blocks = ap_db.get(normalize(pname), [])
                aps = [_leaf(units_cache, sub, u["cards"], root,
                             u["title"], "AP", [u["title"]],
                             folder.name, sub.name)
                       for u, sub in _blocks_to_subfolders(folder, blocks)]
                prods.append({"name": pname, "kind": "AP_GROUP",
                              "cards_total": sum(a["cards_total"] for a in aps),
                              "missing_total": sum(a["missing_total"] for a in aps),
                              "available": any(a["available"] for a in aps),
                              "units": aps})
        cycles.append({"n": n, "products": prods})

    sagas = []
    for sname, folder_name, expansions in hierarchy.SAGAS:
        folder = _find_folder(folder_name, index)
        exp_scen = {normalize(en): sc for en, sc in expansions}
        units = []
        if folder is not None:
            blocks = saga_db.get(normalize(sname), [])
            for u, sub in _blocks_to_subfolders(folder, blocks):
                scen = exp_scen.get(normalize(u["title"] or ""), [])
                units.append(_leaf(units_cache, sub, u["cards"], root,
                                   u["title"], "EXPANSION", scen,
                                   folder.name, sub.name))
        sagas.append({"name": sname, "kind": "SAGA", "units": units,
                      "cards_total": sum(u["cards_total"] for u in units),
                      "missing_total": sum(u["missing_total"] for u in units),
                      "available": any(u["available"] for u in units)})

    result = {"root": str(root), "cycles": cycles, "sagas": sagas,
              "units": units_cache}
    _attach_images(result)
    return result


def _attach_images(cat: dict) -> None:
    """Attach a Hall of Beorn box-art filename to each product/unit by name."""
    from .hallofbeorn import load_reference

    ref = load_reference() or {}
    img: dict[str, str] = {}
    for p in ref.get("products", []):
        img.setdefault(normalize(p["name"]), p["image"].rsplit("/", 1)[-1])

    def first_unit_img(node: dict):
        for u in node.get("units", []):
            if u.get("image"):
                return u["image"]
        return None

    def setimg(node: dict) -> None:
        node["image"] = img.get(normalize(node.get("name", "")))

    for cy in cat["cycles"]:
        for p in cy["products"]:
            for u in p.get("units", []):
                setimg(u)
            setimg(p)
            if not p["image"]:                 # AP group -> first pack's image
                p["image"] = first_unit_img(p)
    for s in cat["sagas"]:
        for u in s["units"]:
            setimg(u)
        setimg(s)
        if not s["image"]:
            s["image"] = first_unit_img(s)
