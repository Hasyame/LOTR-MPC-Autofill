"""Scrape Hall of Beorn for the true card list of each scenario.

hallofbeorn.com/LotR/Scenarios/ lists every scenario grouped by cycle/set; each
scenario detail page gives its encounter/quest card list with quantities per
difficulty. That is the reliable reference for how many (and which) cards a
set/chapter needs — RingsDB only has player cards.

We scrape the index + each scenario once and cache the result to JSON. Names are
later cross-referenced with the local library (see ``database.py``). Zero
external deps (``urllib`` + ``re`` + ``html``).
"""

from __future__ import annotations

import html
import json
import re
import time
import urllib.request
from pathlib import Path
from typing import Optional

BASE_URL = "https://hallofbeorn.com"
SCENARIOS_URL = f"{BASE_URL}/LotR/Scenarios/"
PRODUCTS_URL = f"{BASE_URL}/LotR/Products"
CACHE_FILE = Path.home() / ".lotr-autofill" / "hallofbeorn.json"

_H3 = re.compile(r"<h3[^>]*>(.*?)</h3>", re.DOTALL)
_PRODUCT = re.compile(
    r'<a title="([^"]+)" href="/LotR/Products/[^"]+">\s*'
    r'<img src="(https://[^"?]+/Images/Products/[^"?]+)"', re.DOTALL)
_CODE_SUFFIX = re.compile(r"\s*\([A-Z0-9]+\)$")
_SCEN_LINK = re.compile(r'<a\b[^>]*href="/LotR/Scenarios/([^"]+)"[^>]*>(.*?)</a>',
                        re.DOTALL)
_CARD_ROW = re.compile(
    r'<a title="([^"]+)"[^>]*>\s*<span[^>]*width:300px[^>]*>[^<]*</span>\s*</a>'
    r'\s*<span[^>]*width:60px[^>]*>([^<]*)</span>'
    r'\s*<span[^>]*width:60px[^>]*>([^<]*)</span>'
    r'\s*<span[^>]*width:60px[^>]*>([^<]*)</span>',
    re.DOTALL)
_TAG = re.compile(r"<[^>]+>")


def _get(url: str) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": "LOTRAutofill"})
    with urllib.request.urlopen(req, timeout=30) as resp:  # noqa: S310
        return resp.read()


def _clean(text: str) -> str:
    return html.unescape(_TAG.sub("", text)).strip()


def _num(x: str) -> int:
    x = x.strip()
    return 0 if x in ("", "-") else int(x)


# --------------------------------------------------------------------------- #
# Scraping
# --------------------------------------------------------------------------- #
def fetch_index() -> list[dict]:
    """All scenarios as ``{cycle, name, slug}`` (campaign duplicates skipped)."""
    page = _get(SCENARIOS_URL).decode("utf-8", "replace")
    tokens: list[tuple[int, str, object]] = []
    for m in _H3.finditer(page):
        tokens.append((m.start(), "cycle", _clean(m.group(1))))
    for m in _SCEN_LINK.finditer(page):
        tokens.append((m.start(), "link", (m.group(1), _clean(m.group(2)))))
    tokens.sort(key=lambda t: t[0])

    out: list[dict] = []
    cycle: Optional[str] = None
    for _pos, kind, val in tokens:
        if kind == "cycle":
            cycle = val  # type: ignore[assignment]
        else:
            slug, name = val  # type: ignore[misc]
            if name.endswith("(Campaign)"):
                continue
            out.append({"cycle": cycle, "name": name, "slug": slug})
    return out


def fetch_scenario_cards(slug: str) -> dict[str, dict]:
    """``{card_name: {'normal': n, 'nightmare': n}}`` for one scenario."""
    page = _get(f"{SCENARIOS_URL}{slug}").decode("utf-8", "replace")
    cards: dict[str, dict] = {}
    for m in _CARD_ROW.finditer(page):
        name = _clean(m.group(1))
        cards[name] = {"normal": _num(m.group(2)), "nightmare": _num(m.group(4))}
    return cards


def fetch_products() -> list[dict]:
    """Products with box images as ``{name, image}`` (code suffix stripped)."""
    page = _get(PRODUCTS_URL).decode("utf-8", "replace")
    out: list[dict] = []
    for m in _PRODUCT.finditer(page):
        name = _CODE_SUFFIX.sub("", html.unescape(m.group(1))).strip()
        out.append({"name": name, "image": m.group(2)})
    return out


def build_reference(cache_file: Path = CACHE_FILE, pause: float = 0.3,
                    progress=None) -> dict:
    """Scrape the index + every scenario + product images; cache the result."""
    index = fetch_index()
    scenarios = []
    for i, s in enumerate(index):
        if progress:
            progress(i + 1, len(index), s["name"])
        try:
            cards = fetch_scenario_cards(s["slug"])
        except Exception:
            cards = {}
        scenarios.append({**s, "cards": cards})
        time.sleep(pause)
    try:
        products = fetch_products()
    except Exception:
        products = []
    ref = {"generated_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
           "scenarios": scenarios, "products": products}
    cache_file.parent.mkdir(parents=True, exist_ok=True)
    cache_file.write_text(json.dumps(ref, ensure_ascii=False), encoding="utf-8")
    return ref


def load_reference(cache_file: Path = CACHE_FILE) -> Optional[dict]:
    if Path(cache_file).exists():
        return json.loads(Path(cache_file).read_text(encoding="utf-8"))
    return None
