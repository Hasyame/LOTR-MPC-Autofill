"""Local web server for the LOTRAutofill GUI (Python standard library only).

Serves a single-page UI and a small JSON API that reuses the CLI's building
blocks: browse the card library, generate ``order.xml`` for chosen
sets/chapters, and import a RingsDB deck. Bind to localhost only.
"""

from __future__ import annotations

import json
import threading
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from ..build import BuildOptions, build
from ..database import build_database
from ..sets import default_library_root, discover_chapters, discover_sets
from ..upload.mpc_xml import plan_to_xml
from ..upload.plan import plan_from_manifest
from .page import PAGE


def run_server(root: Path | None = None, host: str = "127.0.0.1",
               port: int = 8765, out_dir: Path | None = None,
               open_browser: bool = True) -> None:
    root = Path(root) if root else default_library_root()
    out_dir = Path(out_dir) if out_dir else Path("MPC_XML")
    out_dir.mkdir(parents=True, exist_ok=True)

    handler = _make_handler(root.resolve(), out_dir.resolve())
    httpd = ThreadingHTTPServer((host, port), handler)
    url = f"http://{host}:{port}/"
    print(f"LOTRAutofill GUI running at {url}\nLibrary: {root.resolve()}\n"
          "Press Ctrl+C to stop.")
    if open_browser:
        threading.Timer(0.5, lambda: webbrowser.open(url)).start()
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping.")
        httpd.shutdown()


def _make_handler(root: Path, out_dir: Path):
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
            length = int(self.headers.get("Content-Length", 0))
            if not length:
                return {}
            return json.loads(self.rfile.read(length).decode("utf-8"))

        # ---- routing ----------------------------------------------------- #
        def do_GET(self):
            if self.path == "/" or self.path.startswith("/index"):
                self._send(200, PAGE.encode("utf-8"), "text/html; charset=utf-8")
            elif self.path == "/api/library":
                self._json(_library(root))
            else:
                self._json({"error": "not found"}, 404)

        def do_POST(self):
            try:
                if self.path == "/api/pick":
                    self._json(_pick(root, out_dir, self._body()))
                elif self.path == "/api/deck":
                    self._json(_deck(out_dir, self._body()))
                else:
                    self._json({"error": "not found"}, 404)
            except Exception as exc:  # surface errors to the UI
                self._json({"error": str(exc)}, 500)

    return Handler


# --------------------------------------------------------------------------- #
# API implementations (reuse the CLI building blocks)
# --------------------------------------------------------------------------- #
def _library(root: Path) -> dict:
    db = build_database(root)
    # Trim the heavy per-card lists; the UI needs names + counts + review.
    for s in db["sets"]:
        for ch in s["chapters"]:
            ch.pop("cards", None)
    return db


def _unit_folder(root: Path, set_name: str, chapter: str | None) -> Path | None:
    set_folder = next((s for s in discover_sets(root) if s.name == set_name), None)
    if set_folder is None:
        return None
    if not chapter:
        return set_folder
    return next((c for c in discover_chapters(set_folder) if c.name == chapter), None)


def _build_unit_xml(folder: Path, label: str, out_dir: Path,
                    stock: str, foil: bool) -> dict:
    report = build(folder, BuildOptions(interactive=False))
    manifest = {"root": str(report.root),
                "cards": [e.to_dict(report.root) for e in report.entries]}
    plan = plan_from_manifest(manifest)
    out = out_dir / f"{_slug(label)}.order.xml"
    out.write_text(plan_to_xml(plan, stock=stock, foil=foil), encoding="utf-8")
    return {"label": label, "order_xml": str(out),
            "cards": plan.total_cards, "fronts": len(plan.unique_fronts)}


def _pick(root: Path, out_dir: Path, body: dict) -> dict:
    stock = body.get("stock", "(S33) Superior Smooth")
    foil = bool(body.get("foil"))
    results = []
    for unit in body.get("units", []):
        set_name = unit.get("set")
        chapter = unit.get("chapter")
        folder = _unit_folder(root, set_name, chapter)
        if folder is None:
            continue
        label = f"{set_name} — {chapter}" if chapter else set_name
        results.append(_build_unit_xml(folder, label, out_dir, stock, foil))
    return {"results": results}


def _deck(out_dir: Path, body: dict) -> dict:
    from .. import ringsdb
    from ..backs import CardBacks, find_backs_dir

    source = (body.get("source") or "").strip()
    stock = body.get("stock", "(S33) Superior Smooth")
    foil = bool(body.get("foil"))
    if not source:
        return {"error": "empty deck source"}

    backs = CardBacks(find_backs_dir(default_library_root()))
    catalog = ringsdb.fetch_cards()
    decklist_id = ringsdb.decklist_id_from(source)
    if decklist_id is not None and "\n" not in source:
        deck_name, slots = ringsdb.fetch_decklist_slots(decklist_id)
        resolved, unmatched = ringsdb.resolve_slots(slots, catalog), []
    else:
        entries = ringsdb.parse_decklist_text(source)
        resolved, unmatched = ringsdb.resolve_text_entries(entries, catalog)
        deck_name = "deck"

    manifest, missing = ringsdb.build_manifest(resolved, backs.player)
    plan = plan_from_manifest(manifest)
    out = out_dir / f"{_slug(deck_name)}.order.xml"
    out.write_text(plan_to_xml(plan, stock=stock, foil=foil), encoding="utf-8")
    return {
        "deck": deck_name,
        "order_xml": str(out),
        "cards": plan.total_cards,
        "resolved": len(resolved),
        "unmatched": [u["name"] for u in unmatched],
        "missing_images": [m["name"] for m in missing],
    }


def _slug(name: str) -> str:
    import re
    return re.sub(r"[^A-Za-z0-9]+", "-", name).strip("-").lower() or "order"
