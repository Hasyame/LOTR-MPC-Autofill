"""Command-line interface for LOTRAutofill."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from . import __version__, i18n
from .i18n import t
from .library.build import BuildOptions, build
from .library.model import BuildReport


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
    parser.add_argument(
        "--lang", choices=i18n.LANGS, default=None,
        help="Language for messages: en/fr/es/zh (default: from $LANG, else en).",
    )
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
    a.set_defaults(func=_cmd_autofill)

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
    i18n.set_lang(i18n.resolve_lang(args.lang))
    return args.func(args)


def _cmd_autofill(args: argparse.Namespace) -> int:
    from .mpc.desktop_tool import run_autofill, default_tool_dir

    return run_autofill(
        args.order,
        tool_dir=args.tool_dir or default_tool_dir(),
        browser=args.browser,
        export_pdf=args.export_pdf,
        skip_install=args.skip_install,
    )


def _cmd_upload(args: argparse.Namespace) -> int:
    from .mpc.runner import run

    if not args.manifest.is_file():
        print(t("cli_manifest_not_found", path=args.manifest), file=sys.stderr)
        return 2
    return run(args.manifest, dry_run=args.dry_run, headed=args.headed)


def _cmd_export(args: argparse.Namespace) -> int:
    from .mpc.plan import load_manifest, plan_from_manifest

    if not args.manifest.is_file():
        print(t("cli_manifest_not_found", path=args.manifest), file=sys.stderr)
        return 2
    plan = plan_from_manifest(load_manifest(args.manifest))
    out = args.output or args.manifest.with_name("order.xml")
    _write_order_xml(plan, out, args.stock, args.foil)
    return 0


def _cmd_gui(args: argparse.Namespace) -> int:
    from .web import run_server
    from .library.sets import default_library_root

    run_server(root=args.root or default_library_root(), port=args.port,
               open_browser=args.open_browser, lang=i18n.current_lang())
    return 0


def _cmd_reference(args: argparse.Namespace) -> int:
    from .catalog.hallofbeorn import CACHE_FILE, build_reference

    def progress(i, n, name):
        print(f"\r  {i}/{n}  {name[:48]:<48}", end="", flush=True)

    print(t("cli_scrape_start"))
    ref = build_reference(progress=progress)
    print("\n" + t("cli_scrape_done", n=len(ref["scenarios"]), path=CACHE_FILE))
    return 0


def _cmd_db(args: argparse.Namespace) -> int:
    import json
    from .catalog.database import build_database
    from .library.sets import default_library_root

    root = args.root or default_library_root()
    print(t("cli_indexing", path=root.resolve()))
    db = build_database(root)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(db, indent=2, ensure_ascii=False),
                           encoding="utf-8")

    total_cards = sum(s["cards_total"] for s in db["sets"])
    total_missing = sum(s.get("missing_total", 0) for s in db["sets"])
    ref = t("cli_ref_on") if db.get("has_reference") else t("cli_ref_off")
    print("\n" + t("cli_db_summary", sets=len(db["sets"]), cards=total_cards,
                    ref=ref, missing=total_missing) + "\n")
    for s in db["sets"]:
        missing = s.get("missing_total", 0)
        if args.missing_only and missing == 0:
            continue
        chapters = f", {len(s['chapters'])} chapters" if s["has_chapters"] else ""
        flag = "  " + t("cli_missing_flag", n=missing) if missing else ""
        name = s.get("display", s["name"])
        print(f"  {name:<40} {s['cards_total']:>4} cards{chapters}{flag}")
        for ch in s["chapters"]:
            if not ch["missing"]:
                continue
            where = f"{ch.get('display', ch['name'])}: " if s["has_chapters"] else ""
            shown = ", ".join(ch["missing"][:6]) + ("…" if len(ch["missing"]) > 6 else "")
            print(f"      {t('cli_missing_prefix')} {where}{shown}")
    print("\n" + t("cli_db_written", path=args.output))
    return 0


def _cmd_sets(args: argparse.Namespace) -> int:
    from .library.sets import discover_sets, default_library_root, display_name

    root = args.root or default_library_root()
    sets = discover_sets(root)
    if not sets:
        print(t("cli_no_sets", path=root.resolve()))
        return 0
    print(t("cli_printable_sets", path=root.resolve()))
    for i, s in enumerate(sets, 1):
        print(f"  [{i}] {display_name(s.name)}")
    return 0


def _cmd_pick(args: argparse.Namespace) -> int:
    from .library.sets import (discover_sets, discover_chapters, default_library_root,
                       display_name)
    from .library.build import BuildOptions, build
    from .mpc.plan import plan_from_manifest
    from .library.interactive import default_enabled

    root = args.root or default_library_root()
    sets = discover_sets(root)
    if not sets:
        print(t("cli_no_sets", path=root.resolve()))
        return 1

    chosen = _choose_sets(sets)
    if not chosen:
        print(t("cli_nothing_selected"))
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
        print(t("cli_nothing_selected"))
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
    from .library.sets import display_name
    print("\n" + t("cli_set_has_chapters", name=display_name(set_folder.name),
                    n=len(chapters)))
    for i, ch in enumerate(chapters, 1):
        print(f"  [{i}] {display_name(ch.name)}")
    print("  " + t("cli_all_chapters"))
    try:
        raw = input(t("cli_prompt_chapters")).strip().lower()
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
    from .library.sets import display_name
    print(t("cli_which_sets"))
    for i, s in enumerate(sets, 1):
        print(f"  [{i}] {display_name(s.name)}")
    print("  " + t("cli_all"))
    try:
        raw = input(t("cli_prompt_sets")).strip().lower()
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
    from .mpc.mpc_xml import plan_to_xml

    if plan.missing_files:
        print(t("cli_img_missing", n=len(plan.missing_files)))
    xml = plan_to_xml(plan, stock=stock, foil=foil)
    out.write_text(xml, encoding="utf-8")
    print(t("cli_orderxml_written", path=out, cards=plan.total_cards,
            fronts=len(plan.unique_fronts)))


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
        print(t("cli_not_a_dir", path=folder), file=sys.stderr)
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
        print("\n" + t("cli_manifest_written", path=out))

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
    print(t("rep_root", path=report.root))
    print(t("rep_unique", n=report.unique_cards))
    print(t("rep_slots", n=report.total_slots))

    by_cat: dict[str, tuple[int, int]] = {}
    for e in report.entries:
        u, s = by_cat.get(e.category, (0, 0))
        by_cat[e.category] = (u + 1, s + e.quantity)
    for cat, (u, s) in sorted(by_cat.items()):
        print(f"  {cat:<10} {u:>3} cards / {s:>3} slots")

    _section(t("sec_double"), report.double_sided_pairs,
             lambda m: f"{m['source']} #{m['number']} [{m['kind']}]: "
                       f"{m['face']} / {m['back']}")
    _section(t("sec_fuzzy"), report.fuzzy_matches,
             lambda m: f"{m['source']}: '{m['cardlist']}' -> '{m['file']}' ({m['score']})")
    _section(t("sec_unmatched"), report.unmatched_cardlist,
             lambda m: f"{m['source']}: {m['quantity']}x '{m['name']}' (best {m['best_score']})")
    _section(t("sec_orphan"), report.orphans,
             lambda m: f"{m['source']}: {m['file']} (side {m['side']})")
    _section(t("sec_auto"), report.auto_included,
             lambda m: f"{m['source']}: {m['file']}")
    _section(t("sec_warnings"), report.warnings, lambda w: str(w))


def _section(title, items, fmt) -> None:
    if not items:
        return
    print(f"\n{title} ({len(items)}):")
    for it in items:
        print(f"  - {fmt(it)}")
