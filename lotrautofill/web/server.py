"""Local web server for the LOTRAutofill GUI (Python standard library only).

Serves a single-page UI and a small JSON API that reuses the CLI's building
blocks: browse the card library, generate ``order.xml`` for chosen
sets/chapters, and resolve a manual card list against the local library. Bind
to localhost only.
"""

from __future__ import annotations

import hashlib
import json
import re
import tempfile
import threading
import urllib.parse
import urllib.request
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from .. import i18n
from ..library.build import BuildOptions, build
from ..catalog.database import build_database
from ..library.sets import (default_library_root, default_output_dir,
                            discover_chapters, discover_sets)
from ..mpc.mpc_xml import plan_to_xml
from ..mpc.plan import plan_from_manifest
from .page import PAGE

# Light thumbnails are cached here (needs Pillow; falls back to the original).
_THUMB_DIR = Path(tempfile.gettempdir()) / "lotr-autofill-thumbs"
_THUMB_MAX = 240
# Hall of Beorn product/box images (fetched from S3, cached).
_PRODUCT_DIR = Path(tempfile.gettempdir()) / "lotr-autofill-products"
_S3_PRODUCTS = "https://s3.amazonaws.com/hallofbeorn-resources/Images/Products/"
_PRODUCT_FILE = re.compile(r"^[A-Za-z0-9_.-]+\.(?:png|jpg|jpeg)$")
_MAX_BODY = 4 * 1024 * 1024  # cap request bodies (cart/manual list) at 4 MB


def run_server(root: Path | None = None, host: str = "127.0.0.1",
               port: int = 8765, out_dir: Path | None = None,
               open_browser: bool = True, lang: str | None = None) -> None:
    root = Path(root) if root else default_library_root()
    out_dir = Path(out_dir) if out_dir else default_output_dir()
    out_dir.mkdir(parents=True, exist_ok=True)

    lang = i18n.resolve_lang(lang)
    handler = _make_handler(root.resolve(), out_dir.resolve())
    httpd = ThreadingHTTPServer((host, port), handler)
    url = f"http://{host}:{port}/"
    print(i18n.t("gui_running", lang=lang, url=url))
    print(i18n.t("gui_library", lang=lang, path=root.resolve()))
    print(i18n.t("gui_stop_hint", lang=lang))
    if open_browser:
        threading.Timer(0.5, lambda: webbrowser.open(url)).start()
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n" + i18n.t("gui_stopping", lang=lang))
        httpd.shutdown()


def _make_handler(root: Path, out_dir: Path):
    # ``root`` can change at runtime (the GUI lets the user pick a folder), so it
    # lives in the cache alongside the expensive-to-build library/catalog index.
    cache: dict = {"root": root}

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):  # quiet
            pass

        # ---- responses --------------------------------------------------- #
        def _send(self, code: int, body: bytes, ctype: str) -> None:
            self.send_response(code)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def _json(self, obj, code: int = 200) -> None:
            self._send(code, json.dumps(obj).encode("utf-8"),
                       "application/json; charset=utf-8")

        def _body(self) -> dict:
            length = int(self.headers.get("Content-Length", 0) or 0)
            if length <= 0:
                return {}
            if length > _MAX_BODY:
                raise ValueError("request body too large")
            return json.loads(self.rfile.read(length).decode("utf-8"))

        # ---- routing ----------------------------------------------------- #
        def do_GET(self):
            parsed = urllib.parse.urlparse(self.path)
            path, query = parsed.path, urllib.parse.parse_qs(parsed.query)
            if path == "/" or path.startswith("/index"):
                self._send(200, PAGE.encode("utf-8"), "text/html; charset=utf-8")
            elif path == "/api/library":
                if "lib" not in cache:
                    cache["lib"] = _library(cache["root"])
                self._json(cache["lib"])
            elif path == "/api/backs":
                self._json(_backs_info(cache["root"]))
            elif path == "/api/cards":
                self._json(_unit_cards(cache["root"], query.get("set", [""])[0],
                                       query.get("chapter", [""])[0]))
            elif path == "/api/thumb":
                self._thumb(query.get("p", [""])[0])
            elif path == "/api/product-image":
                self._binary(*_product_image(query.get("f", [""])[0]),
                             cache_control="max-age=604800")
            else:
                self._json({"error": "not found"}, 404)

        def _binary(self, data, ctype, cache_control="max-age=86400") -> None:
            if data is None:
                self._json({"error": "not found"}, 404)
                return
            self.send_response(200)
            self.send_header("Content-Type", ctype)
            self.send_header("Cache-Control", cache_control)
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        def _thumb(self, rel: str) -> None:
            data, ctype = _thumbnail(cache["root"], rel)
            if data is None:
                self._json({"error": "not found"}, 404)
            else:
                self.send_response(200)
                self.send_header("Content-Type", ctype)
                self.send_header("Cache-Control", "max-age=86400")
                self.send_header("Content-Length", str(len(data)))
                self.end_headers()
                self.wfile.write(data)

        def do_POST(self):
            try:
                if self.path == "/api/pick":
                    self._json(_pick(cache["root"], out_dir, self._body()))
                elif self.path == "/api/autofill":
                    self._json(_autofill(self._body()))
                elif self.path == "/api/cart-export":
                    self._json(_cart_export(cache["root"], out_dir, self._body()))
                elif self.path == "/api/cart-price":
                    self._json(_cart_price(cache["root"], self._body()))
                elif self.path == "/api/set-root":
                    self._json(_set_root(cache, self._body()))
                elif self.path == "/api/manual-list":
                    if "catalog" not in cache:
                        cache["catalog"] = _card_catalog(cache["root"])
                    self._json(_manual_list(cache["catalog"], self._body()))
                else:
                    self._json({"error": "not found"}, 404)
            except Exception as exc:  # surface errors to the UI
                self._json({"error": str(exc)}, 500)

    return Handler


# --------------------------------------------------------------------------- #
# API implementations (reuse the CLI building blocks)
# --------------------------------------------------------------------------- #
def _library(root: Path) -> dict:
    from ..catalog.hallofbeorn import load_reference
    from ..library.matching import normalize

    db = build_database(root)
    # Trim the heavy per-card lists; the UI fetches cards per unit for previews.
    for s in db["sets"]:
        for ch in s["chapters"]:
            ch.pop("cards", None)

    # Canonical sets (Hall of Beorn cycles) the user does NOT have locally,
    # so the UI can show them greyed out and uncheckable.
    _META = ("deck", "kit", "pack", "scenarios")
    unavailable: list[str] = []
    ref = load_reference()
    if ref:
        _map_set_images(db["sets"], ref.get("products", []))
        local = [normalize(re.sub(r"^\d+\s*-\s*", "", s["name"])) for s in db["sets"]]
        seen = set()
        for sc in ref.get("scenarios", []):
            cyc = sc.get("cycle")
            if not cyc:
                continue
            n = normalize(cyc)
            if n in seen:
                continue
            seen.add(n)
            # available if the cycle name is contained in (or contains) a local
            # set name — handles "The Hobbit" vs "The Hobbit Saga" etc.
            available = any(n in loc or loc in n for loc in local)
            if available or any(w in n for w in _META):
                continue
            unavailable.append(cyc)
    db["unavailable_sets"] = unavailable
    db["root"] = str(root)
    return db


def _set_root(cache: dict, body: dict) -> dict:
    """Point the GUI at a different library folder (a path typed by the user).

    Accepts either a library folder directly, or a parent that contains a
    ``sets_folder/``/``toPrint/`` (it descends into it). Clears the cached
    index so the next ``/api/library`` rebuilds from the new folder."""
    lang = i18n.resolve_lang(body.get("lang"))
    raw = (body.get("path") or "").strip().strip('"')
    if not raw:
        return {"error": i18n.t("srv_folder_empty", lang=lang)}
    p = Path(raw).expanduser()
    if not p.is_dir():
        return {"error": i18n.t("srv_folder_not_found", lang=lang, path=raw)}
    cache["root"] = default_library_root(p.resolve())
    cache.pop("lib", None)
    cache.pop("catalog", None)
    return {"ok": True, "root": str(cache["root"])}


def _unit_cards(root: Path, set_name: str, chapter: str) -> dict:
    """Cards of one unit with front/back paths relative to root (for thumbnails)."""
    folder = _unit_folder(root, set_name, chapter or None)
    if folder is None:
        return {"cards": []}
    report = build(folder, BuildOptions(interactive=False))
    cards = []
    for e in report.entries:
        cards.append({
            "name": e.name, "category": e.category, "quantity": e.quantity,
            "double_sided": e.double_sided,
            "front": _rel(e.front, root),
            "back": _rel(e.back, root) if e.back else None,
        })
    return {"cards": cards}


def _rel(p: Path, root: Path) -> str | None:
    try:
        return str(Path(p).resolve().relative_to(root)).replace("\\", "/")
    except ValueError:
        return None


def _thumbnail(root: Path, rel: str) -> tuple[bytes | None, str]:
    """A light JPEG thumbnail of a card image (Pillow); original if unavailable."""
    if not rel:
        return None, ""
    src = (root / rel).resolve()
    if root not in src.parents or not src.is_file():
        return None, ""
    try:
        from PIL import Image
    except Exception:
        return src.read_bytes(), "image/jpeg"  # no Pillow: serve original
    _THUMB_DIR.mkdir(parents=True, exist_ok=True)
    key = hashlib.sha1(f"{src}|{src.stat().st_mtime_ns}".encode()).hexdigest()
    cache = _THUMB_DIR / f"{key}.jpg"
    if not cache.exists():
        try:
            with Image.open(src) as im:
                im = im.convert("RGB")
                im.thumbnail((_THUMB_MAX, _THUMB_MAX))
                im.save(cache, "JPEG", quality=70)
        except Exception:
            return src.read_bytes(), "image/jpeg"
    return cache.read_bytes(), "image/jpeg"


def _product_image(fname: str) -> tuple[bytes | None, str]:
    """A Hall of Beorn product/box image, fetched from S3 and cached."""
    if not fname or not _PRODUCT_FILE.match(fname):
        return None, ""
    _PRODUCT_DIR.mkdir(parents=True, exist_ok=True)
    cache = _PRODUCT_DIR / fname
    if not cache.exists():
        try:
            req = urllib.request.Request(_S3_PRODUCTS + fname,
                                         headers={"User-Agent": "LOTRAutofill"})
            with urllib.request.urlopen(req, timeout=30) as r:  # noqa: S310 (https)
                cache.write_bytes(r.read())
        except Exception:
            return None, ""
    ext = fname.rsplit(".", 1)[-1].lower()
    return cache.read_bytes(), "image/jpeg" if ext in ("jpg", "jpeg") else "image/png"


def _map_set_images(sets: list, products: list) -> None:
    """Attach a Hall of Beorn product image filename to each set/chapter.

    A deluxe box matches a product by name; a cycle (no single product) falls
    back to its first chapter's (adventure pack's) image.
    """
    from ..library.matching import normalize

    index: dict[str, str] = {}
    for p in products:
        index.setdefault(normalize(p["name"]), p["image"])

    def base(url: str | None) -> str | None:
        return url.rsplit("/", 1)[-1] if url else None

    for s in sets:
        set_img = index.get(normalize(s.get("display", s["name"])))
        for ch in s.get("chapters", []):
            cimg = index.get(normalize(ch.get("display", ch["name"])))
            ch["image"] = base(cimg)
            if set_img is None and cimg:
                set_img = cimg
        s["image"] = base(set_img)


def _unit_folder(root: Path, set_name: str, chapter: str | None) -> Path | None:
    set_folder = next((s for s in discover_sets(root) if s.name == set_name), None)
    if set_folder is None:
        return None
    if not chapter:
        return set_folder
    return next((c for c in discover_chapters(set_folder) if c.name == chapter), None)


def _build_unit_xml(folder: Path, label: str, out_dir: Path, stock: str,
                    foil: bool, enc_back: Path | None,
                    ply_back: Path | None) -> dict:
    report = build(folder, BuildOptions(interactive=False, encounter_back=enc_back,
                                        player_back=ply_back))
    manifest = {"root": str(report.root),
                "cards": [e.to_dict(report.root) for e in report.entries]}
    plan = plan_from_manifest(manifest)
    out = out_dir / f"{_slug(label)}.order.xml"
    out.write_text(plan_to_xml(plan, stock=stock, foil=foil), encoding="utf-8")
    return {"label": label, "order_xml": str(out),
            "cards": plan.total_cards, "fronts": len(plan.unique_fronts)}


def _backs_info(root: Path) -> dict:
    from ..library.backs import CardBacks, ENCOUNTER_BACK, PLAYER_BACK, find_backs_dir

    backs = CardBacks(find_backs_dir(root))
    enc, ply = [], []
    for c in backs.choices:
        item = {"label": c.label, "path": _rel(c.path, root)}
        (ply if "player" in c.label.lower() else enc).append(item)
    return {"encounter": enc, "player": ply,
            "default_encounter": Path(ENCOUNTER_BACK).stem,
            "default_player": Path(PLAYER_BACK).stem}


def _resolve_back(root: Path, label) -> Path | None:
    from ..library.backs import CardBacks, find_backs_dir

    if not label:
        return None
    for c in CardBacks(find_backs_dir(root)).choices:
        if c.label == label:
            return c.path
    return None


def _pick(root: Path, out_dir: Path, body: dict) -> dict:
    stock = body.get("stock", "(S33) Superior Smooth")
    foil = bool(body.get("foil"))
    enc_back = _resolve_back(root, body.get("encounter_back"))
    ply_back = _resolve_back(root, body.get("player_back"))
    results = []
    for unit in body.get("units", []):
        set_name = unit.get("set")
        chapter = unit.get("chapter")
        folder = _unit_folder(root, set_name, chapter)
        if folder is None:
            continue
        from ..library.sets import display_name
        label = (f"{display_name(set_name)} — {display_name(chapter)}"
                 if chapter else display_name(set_name))
        results.append(
            _build_unit_xml(folder, label, out_dir, stock, foil, enc_back, ply_back))
    return {"results": results}


def _autofill(body: dict) -> dict:
    from ..mpc.desktop_tool import launch_autofill_terminal

    xml = body.get("order_xml")
    if not xml or not Path(xml).is_file():
        return {"error": i18n.t("srv_order_not_found", lang=i18n.resolve_lang(body.get("lang")))}
    message = launch_autofill_terminal(Path(xml))
    return {"launched": True, "message": message}


def _card_catalog(root: Path) -> dict:
    """Every locally-available card as ``{normalized name: {set, chapter, front,
    name, category}}`` — the reference the Manual List resolves against."""
    from ..library.matching import normalize

    catalog: dict[str, dict] = {}
    for s in discover_sets(root):
        chapters = discover_chapters(s)
        units = ([(c.name, c) for c in chapters] if chapters else [("", s)])
        for chname, folder in units:
            for e in build(folder, BuildOptions(interactive=False)).entries:
                catalog.setdefault(normalize(e.name), {
                    "set": s.name, "chapter": chname, "front": _rel(e.front, root),
                    "name": e.name, "category": e.category})
    return catalog


def _manual_list(catalog: dict, body: dict) -> dict:
    """Resolve a pasted card list against the local library.

    Returns the cards found (with their location + quantity, ready for the cart)
    and the ones with no local image (reported, so the user can decide).
    """
    from ..library.decklist import parse_decklist_text
    from ..library.matching import best_match, normalize

    resolved, missing = [], []
    for qty, name in parse_decklist_text(body.get("text", "")):
        loc = catalog.get(normalize(name))
        if loc is None:
            loc = best_match(name, catalog)[0]
        if loc:
            resolved.append({**loc, "quantity": qty, "query": name})
        else:
            missing.append({"name": name, "quantity": qty})
    return {"resolved": resolved, "missing": missing}


def _resolve_cart_plan(root: Path, body: dict):
    """Resolve the cart (set / chapter / card items) into a single UploadPlan,
    honoring the chosen encounter/player backs. Returns ``None`` if empty."""
    items = body.get("items", [])
    enc_back = _resolve_back(root, body.get("encounter_back"))
    ply_back = _resolve_back(root, body.get("player_back"))

    unit_cache: dict = {}

    def unit_entries(set_name, chapter):
        key = (set_name, chapter or "")
        if key not in unit_cache:
            folder = _unit_folder(root, set_name, chapter or None)
            unit_cache[key] = [] if folder is None else build(
                folder, BuildOptions(interactive=False, encounter_back=enc_back,
                                     player_back=ply_back)).entries
        return unit_cache[key]

    chosen: dict = {}  # front path -> entry (dedupes overlapping items)
    for it in items:
        entries = unit_entries(it.get("set"), it.get("chapter"))
        if it.get("type") == "card":
            entries = [e for e in entries if _rel(e.front, root) == it.get("front")]
            for e in entries:            # a manual-list card carries its quantity
                if it.get("quantity"):
                    e.quantity = int(it["quantity"])
        for e in entries:
            chosen[str(e.front)] = e

    if not chosen:
        return None

    manifest = {"root": str(root), "cards": [
        {"front": str(e.front), "back": str(e.back) if e.back else None,
         "quantity": e.quantity, "name": e.name, "category": e.category,
         "double_sided": e.double_sided} for e in chosen.values()]}
    return plan_from_manifest(manifest)


def _cart_price(root: Path, body: dict) -> dict:
    """Estimate the MPC price of the current cart without writing any file."""
    from ..mpc import pricing

    plan = _resolve_cart_plan(root, body)
    if plan is None:
        return {"error": i18n.t("srv_cart_empty", lang=i18n.resolve_lang(body.get("lang")))}
    stock = body.get("stock", "(S33) Superior Smooth")
    foil = bool(body.get("foil"))
    return {"cards": plan.total_cards, "fronts": len(plan.unique_fronts),
            "price": pricing.estimate(plan.total_cards, stock, foil)}


def _cart_export(root: Path, out_dir: Path, body: dict) -> dict:
    """Resolve the cart (set / chapter / card items) to one order.xml, then
    export it as XML, a PDF proof, or an MPC project."""
    from ..mpc import pricing

    stock = body.get("stock", "(S33) Superior Smooth")
    foil = bool(body.get("foil"))
    fmt = body.get("format", "xml")
    name = body.get("name") or "cart"

    plan = _resolve_cart_plan(root, body)
    if plan is None:
        return {"error": i18n.t("srv_cart_empty", lang=i18n.resolve_lang(body.get("lang")))}

    out = out_dir / f"{_slug(name)}.order.xml"
    out.write_text(plan_to_xml(plan, stock=stock, foil=foil), encoding="utf-8")

    result = {"order_xml": str(out), "cards": plan.total_cards,
              "fronts": len(plan.unique_fronts), "format": fmt,
              "price": pricing.estimate(plan.total_cards, stock, foil)}
    if fmt in ("pdf", "mpc"):
        from ..mpc.desktop_tool import launch_autofill_terminal
        result["message"] = launch_autofill_terminal(out, export_pdf=(fmt == "pdf"))
    return result


def _slug(name: str) -> str:
    return re.sub(r"[^A-Za-z0-9]+", "-", name).strip("-").lower() or "order"
