"""Command-line interface for LOTRAutofill."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from . import __version__
from .build import BuildOptions, build
from .model import BuildReport


def main(argv: list[str] | None = None) -> int:
    # Make report output UTF-8 safe on Windows consoles (accented set names).
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[attr-defined]
        except (AttributeError, ValueError):
            pass

    parser = argparse.ArgumentParser(
        prog="lotr-autofill",
        description="Build MPC proxy orders for The Lord of the Rings LCG.",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    sub = parser.add_subparsers(dest="command", required=True)

    b = sub.add_parser("build", help="Scan a card folder and build a manifest.")
    b.add_argument("folder", type=Path, help="Set or scenario folder to scan.")
    b.add_argument(
        "-o", "--output", type=Path, default=None,
        help="Write the JSON manifest here (default: <folder>/mpc_manifest.json).",
    )
    b.add_argument(
        "--errata", choices=("prefer", "skip", "both"), default="prefer",
        help="How to handle errata/non-errata duplicates (default: prefer).",
    )
    b.add_argument(
        "--player-copies", type=int, default=1,
        help="Copies of each Player card (no cardlist) (default: 1).",
    )
    b.add_argument(
        "--backs-dir", type=Path, default=None,
        help="Card_Backs folder (auto-detected if omitted).",
    )
    b.add_argument(
        "--no-manifest", action="store_true",
        help="Only print the report; do not write the JSON manifest.",
    )
    b.add_argument(
        "--interactive", dest="interactive", action="store_true", default=None,
        help="Prompt for ambiguous cards (backs, face/back, orphans). "
             "Default: on when run in a terminal.",
    )
    b.add_argument(
        "--non-interactive", dest="interactive", action="store_false",
        help="Never prompt; accept all defaults (for scripted runs).",
    )
    b.set_defaults(func=_cmd_build)

    u = sub.add_parser("upload", help="Drive an MPC order from a manifest.")
    u.add_argument("manifest", type=Path, help="mpc_manifest.json from `build`.")
    u.add_argument(
        "--dry-run", action="store_true",
        help="Show the upload plan without launching a browser.",
    )
    u.add_argument(
        "--headed", dest="headed", action="store_true", default=True,
        help="Run the browser visibly (default).",
    )
    u.add_argument(
        "--headless", dest="headed", action="store_false",
        help="Run the browser without a visible window.",
    )
    u.set_defaults(func=_cmd_upload)

    x = sub.add_parser(
        "export", help="Export a manifest as an mpc-autofill order.xml (local files).")
    x.add_argument("manifest", type=Path, help="mpc_manifest.json from `build`.")
    x.add_argument("-o", "--output", type=Path, default=None,
                   help="order.xml path (default: next to the manifest).")
    x.add_argument("--stock", default="(S33) Superior Smooth",
                   help="Cardstock label (default: (S33) Superior Smooth).")
    x.add_argument("--foil", action="store_true", help="Order foil finish.")
    x.set_defaults(func=_cmd_export)

    s = sub.add_parser("sets", help="List printable set folders under a directory.")
    s.add_argument("root", type=Path, nargs="?", default=None,
                   help="Directory to scan (default: toPrint/ if present, else .).")
    s.set_defaults(func=_cmd_sets)

    p = sub.add_parser(
        "pick", help="Pick set folder(s) to print: build + plan + order.xml each.")
    p.add_argument("root", type=Path, nargs="?", default=None,
                   help="Directory to scan (default: toPrint/ if present, else .).")
    p.add_argument("-o", "--out-dir", type=Path, default=Path("MPC_XML"),
                   help="Where to write manifests and order.xml (default: MPC_XML/).")
    p.add_argument("--errata", choices=("prefer", "skip", "both"), default="prefer")
    p.add_argument("--player-copies", type=int, default=1)
    p.add_argument("--stock", default="(S33) Superior Smooth")
    p.add_argument("--foil", action="store_true")
    p.add_argument("--non-interactive", dest="interactive", action="store_false",
                   default=None, help="Accept build defaults, no prompts.")
    p.set_defaults(func=_cmd_pick)

    a = sub.add_parser(
        "autofill",
        help="Run the chilli-axe/mpc-autofill desktop tool on an order.xml.")
    a.add_argument("order", type=Path, help="order.xml from `export`/`pick`.")
    a.add_argument("--browser", default="chrome",
                   help="Browser for the desktop tool (default: chrome).")
    a.add_argument("--pdf", dest="export_pdf", action="store_true",
                   help="Export a PDF proof instead of driving the site "
                        "(no browser/login needed).")
    a.add_argument("--tool-dir", type=Path, default=None,
                   help="Where to clone the desktop tool (default: "
                        "~/.lotr-autofill/mpc-autofill).")
    a.add_argument("--skip-install", action="store_true",
                   help="Assume the tool's venv/deps are already installed.")
    a.add_argument("--keep-images", action="store_true",
                   help="Do not delete temporary RingsDB images after importing.")
    a.set_defaults(func=_cmd_autofill)

    d = sub.add_parser(
        "deck", help="Import a player deck from RingsDB (.txt / id / URL) -> order.xml.")
    d.add_argument("source", help="Decklist .txt file, or a RingsDB decklist id/URL.")
    d.add_argument("-o", "--output", type=Path, default=None,
                   help="order.xml path (default: MPC_XML/<deck>.order.xml).")
    d.add_argument("--player-back", type=Path, default=None,
                   help="Player card-back image (default: auto-detected in "
                        "toPrint/Card_Backs).")
    d.add_argument("--stock", default="(S33) Superior Smooth")
    d.add_argument("--foil", action="store_true")
    d.add_argument("--cache", type=Path, default=None,
                   help="Temp folder for downloaded card images "
                        "(default: a folder in the OS temp dir).")
    d.set_defaults(func=_cmd_deck)

    db = sub.add_parser(
        "db", help="Index the card library and report missing cards per set/chapter.")
    db.add_argument("root", type=Path, nargs="?", default=None,
                    help="Library dir to scan (default: sets_folder/).")
    db.add_argument("-o", "--output", type=Path, default=Path("MPC_XML/database.json"),
                    help="Where to write the JSON database (default: "
                         "MPC_XML/database.json).")
    db.add_argument("--missing-only", action="store_true",
                    help="Only print sets/chapters that have missing cards.")
    db.set_defaults(func=_cmd_db)

    ref = sub.add_parser(
        "reference",
        help="Scrape Hall of Beorn for the true card list of every scenario "
             "(cached for `db`/`gui` missing-card detection).")
    ref.set_defaults(func=_cmd_reference)

    g = sub.add_parser("gui", help="Launch the local web GUI (browse + generate).")
    g.add_argument("root", type=Path, nargs="?", default=None,
                   help="Library dir (default: sets_folder/).")
    g.add_argument("--port", type=int, default=8765, help="Port (default: 8765).")
    g.add_argument("--no-browser", dest="open_browser", action="store_false",
                   default=True, help="Do not open a browser automatically.")
    g.set_defaults(func=_cmd_gui)

    args = parser.parse_args(argv)
    return args.func(args)


def _cmd_autofill(args: argparse.Namespace) -> int:
    from .upload.desktop_tool import run_autofill, default_tool_dir

    code = run_autofill(
        args.order,
        tool_dir=args.tool_dir or default_tool_dir(),
        browser=args.browser,
        export_pdf=args.export_pdf,
        skip_install=args.skip_install,
    )
    # After a real import (not a PDF), delete any temporary RingsDB card images
    # this order referenced — they were only needed to upload into MPC.
    if code == 0 and not args.export_pdf and not args.keep_images:
        _clean_ringsdb_images(args.order)
    return code


def _clean_ringsdb_images(order_xml: Path) -> None:
    from xml.etree import ElementTree as ET
    from . import ringsdb

    try:
        tree = ET.parse(order_xml)
    except Exception:
        return
    paths = [Path(c.text) for c in tree.iter("id") if c.text]
    removed = ringsdb.clean_images(referenced=paths)
    if removed:
        print(f"Cleaned up {removed} temporary RingsDB image(s).")


def _cmd_upload(args: argparse.Namespace) -> int:
    from .upload.runner import run

    if not args.manifest.is_file():
        print(f"error: manifest not found: {args.manifest}", file=sys.stderr)
        return 2
    return run(args.manifest, dry_run=args.dry_run, headed=args.headed)


def _cmd_export(args: argparse.Namespace) -> int:
    from .upload.plan import load_manifest, plan_from_manifest
    from .upload.mpc_xml import plan_to_xml

    if not args.manifest.is_file():
        print(f"error: manifest not found: {args.manifest}", file=sys.stderr)
        return 2
    plan = plan_from_manifest(load_manifest(args.manifest))
    out = args.output or args.manifest.with_name("order.xml")
    _write_order_xml(plan, out, args.stock, args.foil)
    return 0


def _cmd_deck(args: argparse.Namespace) -> int:
    from . import ringsdb
    from .backs import CardBacks, find_backs_dir
    from .sets import default_library_root
    from .upload.plan import plan_from_manifest

    image_dir = args.cache or ringsdb.IMAGE_DIR

    # Resolve the player card-back (local Card_Backs, unless overridden).
    player_back = args.player_back
    if player_back is None:
        backs = CardBacks(find_backs_dir(default_library_root()))
        player_back = backs.player
    if player_back is None:
        print("! No Player card-back found (toPrint/Card_Backs). "
              "Pass --player-back; order.xml will have no cardback otherwise.")

    print("Fetching RingsDB card catalog...")
    catalog = ringsdb.fetch_cards()

    source = args.source
    deck_name = Path(source).stem if Path(source).is_file() else "deck"
    decklist_id = ringsdb.decklist_id_from(source)

    if Path(source).is_file():
        entries = ringsdb.parse_decklist_text(Path(source).read_text(encoding="utf-8"))
        if not entries:
            print(f"No decklist lines parsed from {source}", file=sys.stderr)
            return 2
        resolved, unmatched = ringsdb.resolve_text_entries(entries, catalog)
    elif decklist_id is not None:
        deck_name, slots = ringsdb.fetch_decklist_slots(decklist_id)
        resolved, unmatched = ringsdb.resolve_slots(slots, catalog), []
    else:
        print(f"error: '{source}' is not a file, RingsDB id, or decklist URL",
              file=sys.stderr)
        return 2

    print(f"Deck '{deck_name}': {len(resolved)} card(s) resolved, "
          f"downloading images to a temp folder...")
    manifest, missing = ringsdb.build_manifest(resolved, player_back, image_dir)

    for u in unmatched:
        print(f"  UNMATCHED: {u['quantity']}x '{u['name']}' (best {u['best_score']})")
    for m in missing:
        print(f"  NO IMAGE: {m['name']} ({m['code']})")
    fuzzy = [r for r in resolved if r.match == "fuzzy"]
    for r in fuzzy:
        print(f"  fuzzy: '{r.query}' -> '{r.card['name']}'")

    plan = plan_from_manifest(manifest)
    out_dir = Path("MPC_XML")
    out_dir.mkdir(parents=True, exist_ok=True)
    out = args.output or out_dir / f"{_slug(deck_name)}.order.xml"
    _write_order_xml(plan, out, args.stock, args.foil)
    print(f"\nCard images are temporary (in {image_dir}); `autofill` deletes them "
          "after importing into MPC. They are never committed to git.")
    return 0


def _cmd_gui(args: argparse.Namespace) -> int:
    from .webgui import run_server
    from .sets import default_library_root

    run_server(root=args.root or default_library_root(), port=args.port,
               open_browser=args.open_browser)
    return 0


def _cmd_reference(args: argparse.Namespace) -> int:
    from .hallofbeorn import CACHE_FILE, build_reference

    def progress(i, n, name):
        print(f"\r  {i}/{n}  {name[:48]:<48}", end="", flush=True)

    print("Scraping Hall of Beorn scenarios (one-time; cached)...")
    ref = build_reference(progress=progress)
    print(f"\nCached {len(ref['scenarios'])} scenarios to {CACHE_FILE}")
    return 0


def _cmd_db(args: argparse.Namespace) -> int:
    import json
    from .database import build_database
    from .sets import default_library_root

    root = args.root or default_library_root()
    print(f"Indexing card library under {root.resolve()} ...")
    db = build_database(root)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(db, indent=2, ensure_ascii=False),
                           encoding="utf-8")

    total_cards = sum(s["cards_total"] for s in db["sets"])
    total_missing = sum(s.get("missing_total", 0) for s in db["sets"])
    ref = "Hall of Beorn cross-reference on" if db.get("has_reference") else \
        "no Hall of Beorn reference (run `lotr-autofill reference` first)"
    print(f"\n{len(db['sets'])} sets, {total_cards} cards indexed "
          f"({ref}). {total_missing} missing card(s):\n")
    for s in db["sets"]:
        missing = s.get("missing_total", 0)
        if args.missing_only and missing == 0:
            continue
        chapters = f", {len(s['chapters'])} chapters" if s["has_chapters"] else ""
        flag = f"  [{missing} MISSING]" if missing else ""
        name = s.get("display", s["name"])
        print(f"  {name:<40} {s['cards_total']:>4} cards{chapters}{flag}")
        for ch in s["chapters"]:
            if not ch["missing"]:
                continue
            where = f"{ch.get('display', ch['name'])}: " if s["has_chapters"] else ""
            shown = ", ".join(ch["missing"][:6]) + ("…" if len(ch["missing"]) > 6 else "")
            print(f"      missing — {where}{shown}")
    print(f"\nDatabase written to: {args.output}")
    return 0


def _cmd_sets(args: argparse.Namespace) -> int:
    from .sets import discover_sets, default_library_root, display_name

    root = args.root or default_library_root()
    sets = discover_sets(root)
    if not sets:
        print(f"No printable set folders found under {root.resolve()}")
        return 0
    print(f"Printable sets under {root.resolve()}:")
    for i, s in enumerate(sets, 1):
        print(f"  [{i}] {display_name(s.name)}")
    return 0


def _cmd_pick(args: argparse.Namespace) -> int:
    from .sets import (discover_sets, discover_chapters, default_library_root,
                       display_name)
    from .build import BuildOptions, build
    from .upload.plan import plan_from_manifest
    from .interactive import default_enabled

    root = args.root or default_library_root()
    sets = discover_sets(root)
    if not sets:
        print(f"No printable set folders found under {root.resolve()}")
        return 1

    chosen = _choose_sets(sets)
    if not chosen:
        print("Nothing selected.")
        return 0

    # Resolve each chosen set into print units: the whole set, or its chapters.
    units: list[tuple[str, Path]] = []
    for s in chosen:
        chapters = discover_chapters(s)
        if not chapters:
            units.append((display_name(s.name), s))
            continue
        picked = _choose_chapters(s, chapters)
        for ch in picked:
            units.append((f"{display_name(s.name)} — {display_name(ch.name)}", ch))

    if not units:
        print("Nothing selected.")
        return 0

    interactive = default_enabled() if args.interactive is None else args.interactive
    options = BuildOptions(errata=args.errata, player_copies=args.player_copies,
                           interactive=interactive)
    args.out_dir.mkdir(parents=True, exist_ok=True)

    for label, folder in units:
        print(f"\n=== {label} ===")
        report = build(folder, options)
        print_report(report)
        slug = _slug(label)
        write_manifest(report, args.out_dir / f"{slug}.json", options)
        plan = plan_from_manifest(_manifest_dict(report, options))
        _write_order_xml(plan, args.out_dir / f"{slug}.order.xml", args.stock, args.foil)
    return 0


def _choose_chapters(set_folder: Path, chapters: list) -> list:
    from .sets import display_name
    print(f"\n'{display_name(set_folder.name)}' has {len(chapters)} chapters:")
    for i, ch in enumerate(chapters, 1):
        print(f"  [{i}] {display_name(ch.name)}")
    print("  [a] all chapters (one order.xml each)")
    try:
        raw = input("Chapters to print (comma-separated), 'a' for all: ").strip().lower()
    except EOFError:
        return list(chapters)
    if raw in ("a", "all", ""):
        return list(chapters)
    picks = []
    for tok in raw.replace(" ", "").split(","):
        if tok.isdigit() and 1 <= int(tok) <= len(chapters):
            picks.append(chapters[int(tok) - 1])
    return picks


def _choose_sets(sets: list) -> list:
    from .sets import display_name
    print("Which set(s) do you want to print?")
    for i, s in enumerate(sets, 1):
        print(f"  [{i}] {display_name(s.name)}")
    print("  [a] all")
    try:
        raw = input("Enter numbers (comma-separated), 'a' for all: ").strip().lower()
    except EOFError:
        return []
    if raw in ("a", "all"):
        return list(sets)
    picks = []
    for tok in raw.replace(" ", "").split(","):
        if tok.isdigit() and 1 <= int(tok) <= len(sets):
            picks.append(sets[int(tok) - 1])
    return picks


def _write_order_xml(plan, out: Path, stock: str, foil: bool) -> None:
    from .upload.mpc_xml import plan_to_xml

    if plan.missing_files:
        print(f"! {len(plan.missing_files)} image(s) missing — order.xml may be "
              "incomplete.")
    xml = plan_to_xml(plan, stock=stock, foil=foil)
    out.write_text(xml, encoding="utf-8")
    print(f"order.xml written to: {out}  "
          f"({plan.total_cards} cards, {len(plan.unique_fronts)} fronts)")


def _manifest_dict(report, options) -> dict:
    # Build the same dict write_manifest serializes, without a file round-trip.
    return {
        "root": str(report.root),
        "cards": [e.to_dict(report.root) for e in report.entries],
    }


def _slug(name: str) -> str:
    import re
    return re.sub(r"[^A-Za-z0-9]+", "-", name).strip("-").lower() or "set"


def _cmd_build(args: argparse.Namespace) -> int:
    folder: Path = args.folder
    if not folder.is_dir():
        print(f"error: not a directory: {folder}", file=sys.stderr)
        return 2

    options = BuildOptions(
        errata=args.errata,
        player_copies=args.player_copies,
        backs_dir=args.backs_dir,
        interactive=args.interactive,
    )
    report = build(folder, options)
    print_report(report)

    if not args.no_manifest:
        out = args.output or (folder.resolve() / "mpc_manifest.json")
        write_manifest(report, out, options)
        print(f"\nManifest written to: {out}")

    return 0


def write_manifest(report: BuildReport, out: Path, options: BuildOptions) -> None:
    manifest = {
        "version": __version__,
        "root": str(report.root),
        "options": {
            "errata": options.errata,
            "player_copies": options.player_copies,
        },
        "summary": {
            "unique_cards": report.unique_cards,
            "total_slots": report.total_slots,
            "unmatched_cardlist": len(report.unmatched_cardlist),
            "fuzzy_matches": len(report.fuzzy_matches),
            "double_sided_pairs": len(report.double_sided_pairs),
            "orphans": len(report.orphans),
            "auto_included": len(report.auto_included),
        },
        "cards": [e.to_dict(report.root) for e in report.entries],
        "unmatched_cardlist": report.unmatched_cardlist,
        "fuzzy_matches": report.fuzzy_matches,
        "double_sided_pairs": report.double_sided_pairs,
        "orphans": report.orphans,
        "auto_included": report.auto_included,
        "warnings": report.warnings,
    }
    out.write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")


def print_report(report: BuildReport) -> None:
    print(f"Root: {report.root}")
    print(f"Unique cards : {report.unique_cards}")
    print(f"Total slots  : {report.total_slots}")

    by_cat: dict[str, tuple[int, int]] = {}
    for e in report.entries:
        u, s = by_cat.get(e.category, (0, 0))
        by_cat[e.category] = (u + 1, s + e.quantity)
    for cat, (u, s) in sorted(by_cat.items()):
        print(f"  {cat:<10} {u:>3} cards / {s:>3} slots")

    _section("Double-sided pairs (verify face/back)", report.double_sided_pairs,
             lambda m: f"{m['source']} #{m['number']} [{m['kind']}]: "
                       f"{m['face']} / {m['back']}")
    _section("Fuzzy (typo) matches — please verify", report.fuzzy_matches,
             lambda m: f"{m['source']}: '{m['cardlist']}' -> '{m['file']}' ({m['score']})")
    _section("UNMATCHED cardlist entries", report.unmatched_cardlist,
             lambda m: f"{m['source']}: {m['quantity']}x '{m['name']}' (best {m['best_score']})")
    _section("Orphan sides (need face/back — check these)", report.orphans,
             lambda m: f"{m['source']}: {m['file']} (side {m['side']})")
    _section("Auto-included (not in cardlist, added at 1)", report.auto_included,
             lambda m: f"{m['source']}: {m['file']}")
    _section("Warnings", report.warnings, lambda w: str(w))


def _section(title, items, fmt) -> None:
    if not items:
        return
    print(f"\n{title} ({len(items)}):")
    for it in items:
        print(f"  - {fmt(it)}")
