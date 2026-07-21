"""Import a player deck from RingsDB and turn it into an order.xml.

Input can be:
  * a decklist ``.txt`` file (lines like ``3x Gandalf`` / ``2 Steward of Gondor``)
  * a RingsDB decklist id or URL (e.g. ``12345`` or a ringsdb.com/decklist/... link)

Card names are resolved against RingsDB's card list with the same normalized +
fuzzy matching used for local sets; images are downloaded (and cached) from
RingsDB. The result is a manifest dict compatible with ``plan_from_manifest`` so
the existing ``order.xml`` export is reused. Player cards all get the Player back.

Zero external dependencies — uses ``urllib`` from the standard library.
"""

from __future__ import annotations

import json
import re
import tempfile
import urllib.request
from pathlib import Path
from typing import Optional

from .matching import best_match, normalize

BASE_URL = "https://ringsdb.com"
CARDS_URL = f"{BASE_URL}/api/public/cards/"
CARD_URL = f"{BASE_URL}/api/public/card/{{code}}.json"
DECKLIST_URL = f"{BASE_URL}/api/public/decklist/{{id}}.json"

# Card catalog (metadata JSON only) persists in the user's home cache.
CATALOG_DIR = Path.home() / ".lotr-autofill"
# Downloaded CARD IMAGES are temporary: kept only long enough to import into
# MPC, stored in the OS temp dir (outside any repo, so never committed to git).
IMAGE_DIR = Path(tempfile.gettempdir()) / "lotr-autofill-ringsdb"

# "3x Gandalf", "3 Gandalf", "Gandalf x3" — with optional trailing "(Pack)".
_LINE_LEADING = re.compile(r"^\s*(\d+)\s*[xX]?\s+(.+?)\s*$")
_LINE_TRAILING = re.compile(r"^\s*(.+?)\s*[xX]\s*(\d+)\s*$")
_TRAILING_PACK = re.compile(r"\s*\([^)]*\)\s*$")


# --------------------------------------------------------------------------- #
# HTTP (stdlib)
# --------------------------------------------------------------------------- #
def _get(url: str) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": "LOTRAutofill"})
    with urllib.request.urlopen(req, timeout=30) as resp:  # noqa: S310 (https only)
        return resp.read()


def _get_json(url: str):
    return json.loads(_get(url).decode("utf-8"))


# --------------------------------------------------------------------------- #
# Card catalog
# --------------------------------------------------------------------------- #
def fetch_cards(cache_dir: Path = CATALOG_DIR) -> dict[str, dict]:
    """All RingsDB cards as ``{code: card}``, cached to disk for a day-ish."""
    cache_dir.mkdir(parents=True, exist_ok=True)
    cache = cache_dir / "cards.json"
    if cache.exists():
        cards = json.loads(cache.read_text(encoding="utf-8"))
    else:
        cards = _get_json(CARDS_URL)
        cache.write_text(json.dumps(cards), encoding="utf-8")
    return {c["code"]: c for c in cards}


def _card_by_code(code: str, catalog: dict[str, dict]) -> Optional[dict]:
    if code in catalog:
        return catalog[code]
    try:
        return _get_json(CARD_URL.format(code=code))
    except Exception:
        return None


def _name_index(catalog: dict[str, dict]) -> dict[str, dict]:
    return {normalize(c["name"]): c for c in catalog.values() if c.get("name")}


# --------------------------------------------------------------------------- #
# Decklist parsing / fetching
# --------------------------------------------------------------------------- #
def parse_decklist_text(text: str) -> list[tuple[int, str]]:
    """Parse decklist lines into ``(quantity, name)`` pairs.

    Lines without an explicit quantity (section headers, blanks, comments) are
    skipped.
    """
    entries: list[tuple[int, str]] = []
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        m = _LINE_LEADING.match(line)
        if m:
            qty, name = int(m.group(1)), m.group(2)
        else:
            m = _LINE_TRAILING.match(line)
            if not m:
                continue
            name, qty = m.group(1), int(m.group(2))
        name = _TRAILING_PACK.sub("", name).strip()
        if name:
            entries.append((qty, name))
    return entries


def decklist_id_from(arg: str) -> Optional[str]:
    """Return a RingsDB decklist id if ``arg`` is an id or a decklist URL."""
    arg = arg.strip()
    if arg.isdigit():
        return arg
    m = re.search(r"ringsdb\.com/.*?decklist/(?:view/)?(\d+)", arg)
    return m.group(1) if m else None


def fetch_decklist_slots(decklist_id: str) -> tuple[str, dict[str, int]]:
    data = _get_json(DECKLIST_URL.format(id=decklist_id))
    slots = {code: int(q) for code, q in (data.get("slots") or {}).items()}
    return data.get("name") or f"decklist-{decklist_id}", slots


# --------------------------------------------------------------------------- #
# Resolution
# --------------------------------------------------------------------------- #
class Resolved:
    def __init__(self, card: dict, quantity: int, match: str, query: str):
        self.card = card
        self.quantity = quantity
        self.match = match
        self.query = query


def resolve_text_entries(entries: list[tuple[int, str]], catalog: dict[str, dict]
                         ) -> tuple[list[Resolved], list[dict]]:
    index = _name_index(catalog)
    resolved: list[Resolved] = []
    unmatched: list[dict] = []
    for qty, name in entries:
        card, kind, score = best_match(name, index)
        if card is None:
            unmatched.append({"name": name, "quantity": qty,
                              "best_score": round(score, 2)})
            continue
        resolved.append(Resolved(card, qty, kind, name))
    return resolved, unmatched


def resolve_slots(slots: dict[str, int], catalog: dict[str, dict]
                  ) -> tuple[list[Resolved], list[dict]]:
    resolved: list[Resolved] = []
    unmatched: list[dict] = []
    for code, qty in slots.items():
        card = _card_by_code(code, catalog)
        if card is None:
            unmatched.append({"name": code, "quantity": qty, "best_score": 0})
            continue
        resolved.append(Resolved(card, qty, "code", code))
    return resolved


# --------------------------------------------------------------------------- #
# Images
# --------------------------------------------------------------------------- #
def download_image(card: dict, dest_dir: Path = IMAGE_DIR) -> Optional[Path]:
    src = card.get("imagesrc")
    if not src:
        return None
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest = dest_dir / f"{card['code']}.png"
    if not dest.exists() or dest.stat().st_size == 0:
        try:
            dest.write_bytes(_get(f"{BASE_URL}{src}"))
        except Exception:
            return None
    return dest


def clean_images(referenced: Optional[list[Path]] = None) -> int:
    """Delete temporary RingsDB card images.

    With ``referenced``, delete only those paths that live under ``IMAGE_DIR``
    (so local set images are never touched); otherwise clear the whole temp
    image directory. Returns the number of files removed.
    """
    removed = 0
    if referenced is not None:
        for p in referenced:
            p = Path(p)
            try:
                if IMAGE_DIR in p.resolve().parents and p.exists():
                    p.unlink()
                    removed += 1
            except OSError:
                pass
        return removed
    if IMAGE_DIR.exists():
        for p in IMAGE_DIR.glob("*"):
            try:
                p.unlink()
                removed += 1
            except OSError:
                pass
    return removed


# --------------------------------------------------------------------------- #
# Manifest assembly (reuses the existing plan/order.xml pipeline)
# --------------------------------------------------------------------------- #
def build_manifest(resolved: list[Resolved], player_back: Optional[Path],
                   image_dir: Path = IMAGE_DIR) -> tuple[dict, list[dict]]:
    """Turn resolved cards into a manifest dict + a list of missing-image notes."""
    cards: list[dict] = []
    missing: list[dict] = []
    for r in resolved:
        img = download_image(r.card, image_dir)
        if img is None:
            missing.append({"name": r.card.get("name", r.query), "code": r.card["code"]})
            continue
        cards.append({
            "front": str(img),
            "back": str(player_back) if player_back else None,
            "quantity": r.quantity,
            "name": r.card.get("name", r.query),
            "number": r.card["code"],
            "category": "Player",
            "double_sided": False,
            "source": "RingsDB",
            "match": r.match,
        })
    return {"root": str(image_dir), "cards": cards}, missing
