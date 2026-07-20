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
    s.add_argument("root", type=Path, nargs="?", default=Path("."),
                   help="Directory to scan (default: current).")
    s.set_defaults(func=_cmd_sets)

    p = sub.add_parser(
        "pick", help="Pick set folder(s) to print: build + plan + order.xml each.")
    p.add_argument("root", type=Path, nargs="?", default=Path("."),
                   help="Directory to scan for sets (default: current).")
    p.add_argument("-o", "--out-dir", type=Path, default=Path("builds"),
                   help="Where to write manifests and order.xml (default: builds/).")
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

    args = parser.parse_args(argv)
    return args.func(args)


def _cmd_autofill(args: argparse.Namespace) -> int:
    from .upload.desktop_tool import run_autofill, default_tool_dir

    return run_autofill(
        args.order,
        tool_dir=args.tool_dir or default_tool_dir(),
        browser=args.browser,
        export_pdf=args.export_pdf,
        skip_install=args.skip_install,
    )


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


def _cmd_sets(args: argparse.Namespace) -> int:
    from .sets import discover_sets

    sets = discover_sets(args.root)
    if not sets:
        print(f"No printable set folders found under {args.root.resolve()}")
        return 0
    print(f"Printable sets under {args.root.resolve()}:")
    for i, s in enumerate(sets, 1):
        print(f"  [{i}] {s.name}")
    return 0


def _cmd_pick(args: argparse.Namespace) -> int:
    from .sets import discover_sets
    from .build import BuildOptions, build
    from .upload.plan import plan_from_manifest
    from .interactive import default_enabled

    sets = discover_sets(args.root)
    if not sets:
        print(f"No printable set folders found under {args.root.resolve()}")
        return 1

    chosen = _choose_sets(sets)
    if not chosen:
        print("Nothing selected.")
        return 0

    interactive = default_enabled() if args.interactive is None else args.interactive
    options = BuildOptions(errata=args.errata, player_copies=args.player_copies,
                           interactive=interactive)
    args.out_dir.mkdir(parents=True, exist_ok=True)

    for folder in chosen:
        print(f"\n=== {folder.name} ===")
        report = build(folder, options)
        print_report(report)
        slug = _slug(folder.name)
        manifest_path = args.out_dir / f"{slug}.json"
        write_manifest(report, manifest_path, options)
        plan = plan_from_manifest(_manifest_dict(report, options))
        _write_order_xml(plan, args.out_dir / f"{slug}.order.xml", args.stock, args.foil)
    return 0


def _choose_sets(sets: list) -> list:
    print("Which set(s) do you want to print?")
    for i, s in enumerate(sets, 1):
        print(f"  [{i}] {s.name}")
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
