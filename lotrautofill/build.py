"""Orchestration: turn a folder of card images into an MPC build manifest."""

from __future__ import annotations

import re
from collections import OrderedDict, defaultdict
from pathlib import Path
from typing import Optional

from .backs import CardBacks, find_backs_dir
from .interactive import Prompter, default_enabled
from .matching import best_match, normalize
from .model import (
    CARDLIST_CATEGORIES,
    CATEGORY_PLAYER,
    BuildReport,
    CardEntry,
    CardImage,
)
from .parsing import (
    IMAGE_EXTS,
    find_category_folders,
    image_folders_for_category,
    list_images,
)

_CARDLIST_LINE = re.compile(r"^\s*(\d+)\s+(.+?)\s*$")


class BuildOptions:
    def __init__(
        self,
        errata: str = "prefer",     # prefer | skip | both
        player_copies: int = 1,
        backs_dir: Optional[Path] = None,
        interactive: Optional[bool] = None,
        encounter_back: Optional[Path] = None,
        player_back: Optional[Path] = None,
    ):
        self.errata = errata
        self.player_copies = player_copies
        self.backs_dir = backs_dir
        self.interactive = default_enabled() if interactive is None else interactive
        # Explicit common-back overrides (skip the interactive/ default choice).
        self.encounter_back = encounter_back
        self.player_back = player_back


class _Context:
    def __init__(self, backs: CardBacks, prompter: Prompter, options: BuildOptions,
                 report: BuildReport):
        self.backs = backs
        self.prompter = prompter
        self.options = options
        self.report = report
        # Per-category common back, resolved once (possibly interactively).
        self.category_back: dict[str, Optional[Path]] = {}
        # Double-sided pairs emitted for the folder currently being processed,
        # as (entry, face_name, back_name) — so a cardlist quantity can be
        # applied to a double-sided card too.
        self.folder_pairs: list[tuple] = []


def build(root: Path, options: BuildOptions) -> BuildReport:
    root = root.resolve()
    backs_dir = options.backs_dir or find_backs_dir(root)
    backs = CardBacks(backs_dir)
    report = BuildReport(root=root)
    prompter = Prompter(options.interactive)
    ctx = _Context(backs, prompter, options, report)

    if backs_dir is None:
        report.warnings.append(
            "No Card_Backs folder found — single-sided cards will have no back."
        )

    category_folders = find_category_folders(root)
    if not category_folders:
        report.warnings.append(f"No category folders found under {root}")
        return report

    categories = sorted({c for c, _ in category_folders})
    _select_common_backs(ctx, categories)

    for category, folder in category_folders:
        for image_folder in image_folders_for_category(category, folder):
            _build_folder(ctx, category, image_folder)

    return report


def _select_common_backs(ctx: _Context, categories: list[str]) -> None:
    """Resolve, once, the common back image used per category."""
    backs = ctx.backs
    for category in categories:
        override = (ctx.options.player_back if category == CATEGORY_PLAYER
                    else ctx.options.encounter_back)
        if override is not None:
            ctx.category_back[category] = Path(override)
            continue
        default_path = backs.for_category(category)
        if not ctx.prompter.enabled or not backs.choices:
            ctx.category_back[category] = default_path
            continue
        labels = [c.label for c in backs.choices]
        default_idx = next(
            (i for i, c in enumerate(backs.choices) if c.path == default_path), 0
        )
        idx = ctx.prompter.choose(
            f"Common back image for {category} cards?", labels, default_idx
        )
        ctx.category_back[category] = backs.choices[idx].path


def _common_back(ctx: _Context, category: str) -> Optional[Path]:
    return ctx.category_back.get(category, ctx.backs.for_category(category))


def _build_folder(ctx: _Context, category: str, folder: Path) -> None:
    images = list_images(folder)
    if not images:
        return
    source = _rel_source(folder, ctx.report.root)
    cardlist = _load_cardlist(folder) if category in CARDLIST_CATEGORIES else None

    ctx.folder_pairs = []
    groups = _group_by_number(images)
    singles: list[CardImage] = []      # single-sided cards awaiting a quantity
    faces_in_folder = [i for i in images if i.side == "A" or i.side is None]

    for number, imgs in groups.items():
        singles.extend(
            _classify_group(ctx, category, source, number, imgs, faces_in_folder)
        )

    _quantify_singles(ctx, category, source, singles, cardlist, images, folder)


# --------------------------------------------------------------------------- #
# Group classification
# --------------------------------------------------------------------------- #
def _classify_group(
    ctx: _Context,
    category: str,
    source: str,
    number: str,
    imgs: list[CardImage],
    faces_in_folder: list[CardImage],
) -> list[CardImage]:
    """Emit paired/orphan entries for a number-group; return leftover singles."""
    a_sides = [i for i in imgs if i.side == "A"]
    b_sides = [i for i in imgs if i.side == "B"]
    plain = [i for i in imgs if i.side is None]

    # 1) Explicit A/B quest-style pair(s).
    if a_sides or b_sides:
        for face, back in zip(a_sides, b_sides):
            _emit_pair(ctx, category, source, number, face, back, kind="A/B")
        for orphan in a_sides[len(b_sides):]:
            _resolve_orphan(ctx, category, source, orphan, faces_in_folder)
        for orphan in b_sides[len(a_sides):]:
            _resolve_orphan(ctx, category, source, orphan, faces_in_folder)
        return plain  # any no-side images fall through as singles

    # 2) Same number, different names -> double-sided pair(s). When several
    # images share a number (an even count), pair them into consecutive couples
    # in file order: (1st,2nd), (3rd,4th), ... Each couple is one card.
    if len({normalize(i.name) for i in plain}) > 1:
        chosen = _apply_errata(plain, ctx.options.errata)
        for i in range(0, len(chosen) - 1, 2):
            face, back = _order_pair(ctx, source, number, chosen[i], chosen[i + 1])
            _emit_pair(ctx, category, source, number, face, back, kind="same-number")
        return chosen[-1:] if len(chosen) % 2 == 1 else []

    # 3) Same number, same name -> errata duplicate(s): collapse.
    return _apply_errata(plain, ctx.options.errata)


def _emit_pair(ctx, category, source, number, face, back, kind, quantity=1) -> None:
    entry = CardEntry(
        front=face.path,
        back=back.path,
        quantity=quantity,
        name=face.name,
        number=number,
        category=category,
        double_sided=True,
        source=source,
        match="implicit",
        note=f"double-sided ({kind})",
    )
    ctx.report.entries.append(entry)
    ctx.folder_pairs.append((entry, face.name, back.name))
    ctx.report.double_sided_pairs.append(
        {"source": source, "number": number, "kind": kind,
         "face": face.filename, "back": back.filename}
    )


def _order_pair(ctx, source, number, a: CardImage, b: CardImage):
    """Decide which of two same-number images is the face (front)."""
    idx = ctx.prompter.choose(
        f"[{source}] number {number}: which image is the FACE (front)?",
        [a.filename, b.filename],
        default=0,
    )
    return (a, b) if idx == 0 else (b, a)


def _resolve_orphan(ctx, category, source, orphan: CardImage,
                    faces_in_folder: list[CardImage]) -> None:
    """An A/B side with no partner (e.g. branching-quest back).

    A back-side orphan is attached to a chosen face; a face-side orphan gets a
    chosen back. Defaults keep the run non-blocking; the report flags it.
    """
    if orphan.side == "B":
        faces = [f for f in faces_in_folder if f.path != orphan.path]
        labels = [f"FACE: {f.filename}" for f in faces] + ["use common back instead"]
        default = 0 if len(faces) == 1 else len(labels) - 1
        idx = ctx.prompter.choose(
            f"[{source}] back '{orphan.filename}' has no face. Attach to which face?",
            labels, default,
        )
        if idx < len(faces):
            face = faces[idx]
            _emit_pair(ctx, category, source, orphan.number, face, orphan,
                       kind="branching")
            return
        # Fallback: treat the back image as a face with the common back.
        back = _common_back(ctx, category)
        _emit_single(ctx, category, source, orphan, 1, back, match="orphan",
                     note="orphan back, given common back")
    else:  # orphan face
        back = _choose_back_for(ctx, category, source, orphan)
        _emit_single(ctx, category, source, orphan, 1, back, match="orphan",
                     note="orphan face")
    ctx.report.orphans.append(
        {"source": source, "file": orphan.filename, "side": orphan.side}
    )


def _choose_back_for(ctx, category, source, img: CardImage) -> Optional[Path]:
    default = _common_back(ctx, category)
    if not ctx.prompter.enabled or not ctx.backs.choices:
        return default
    labels = [c.label for c in ctx.backs.choices]
    default_idx = next(
        (i for i, c in enumerate(ctx.backs.choices) if c.path == default), 0
    )
    idx = ctx.prompter.choose(
        f"[{source}] back for '{img.filename}'?", labels, default_idx
    )
    return ctx.backs.choices[idx].path


# --------------------------------------------------------------------------- #
# Quantities for single-sided cards
# --------------------------------------------------------------------------- #
def _quantify_singles(ctx, category, source, singles: list[CardImage],
                      cardlist: Optional[list[tuple[int, str]]],
                      all_images: list[CardImage] | None = None,
                      folder: Optional[Path] = None) -> None:
    if not singles and not ctx.folder_pairs:
        return
    back = _common_back(ctx, category)

    if category == CATEGORY_PLAYER:
        for img in singles:
            _emit_single(ctx, category, source, img, ctx.options.player_copies, back,
                         match="implicit")
        return

    if cardlist is None:
        # No cardlist (Player already handled; Quest singles, or missing file).
        for img in singles:
            _emit_single(ctx, category, source, img, 1, back, match="implicit")
        return

    candidates = _candidate_map(singles, ctx.report)
    pair_candidates = _pair_candidate_map(ctx.folder_pairs)
    all_map = _candidate_map(all_images or singles, ctx.report)
    used: set[str] = set()
    for qty, name in cardlist:
        img, kind, score = best_match(name, candidates)
        if img is not None:
            used.add(img.path.name)
            note = ""
            if kind == "fuzzy":
                note = f"cardlist '{name}' -> '{img.name}' ({score:.2f})"
                ctx.report.fuzzy_matches.append(
                    {"source": source, "cardlist": name, "file": img.name,
                     "score": round(score, 2)}
                )
            _emit_single(ctx, category, source, img, qty, back, match=kind, note=note)
            continue

        # A "SideA/SideB" cardlist entry refers to an already-emitted
        # double-sided card: apply the quantity to that pair.
        pair, pkind, pscore = best_match(name, pair_candidates)
        if pair is not None:
            pair.quantity = qty
            if pkind == "fuzzy":
                ctx.report.fuzzy_matches.append(
                    {"source": source, "cardlist": name, "file": pair.name,
                     "score": round(pscore, 2)}
                )
            continue

        # A "Front/Back" entry for a two-sided card whose sides are separate
        # images (possibly different numbers): pair the two named images.
        if "/" in name:
            parts = [p.strip() for p in name.split("/") if p.strip()]
            if len(parts) >= 2:
                f_img, _fk, _fs = best_match(parts[0], candidates)
                b_img, _bk, _bs = best_match(parts[-1], all_map)
                if b_img is None:
                    # The back may be stored without a number prefix (a shared
                    # back like "Edge of the Temple.jpg") — scan raw files.
                    b_img = _raw_back_image(folder, parts[-1])
                if (f_img is not None and b_img is not None
                        and f_img.path != b_img.path):
                    used.add(f_img.path.name)
                    if any(s.path == b_img.path for s in singles):
                        used.add(b_img.path.name)
                    _emit_pair(ctx, category, source, f_img.number, f_img, b_img,
                               kind="cardlist", quantity=qty)
                    continue

        ctx.report.unmatched_cardlist.append(
            {"source": source, "name": name, "quantity": qty,
             "best_score": round(score, 2)}
        )

    # Cards present but not listed -> auto-include at qty 1 (per project rules).
    for img in singles:
        if img.path.name not in used:
            _emit_single(ctx, category, source, img, 1, back, match="auto",
                         note="not in cardlist, included at 1")
            ctx.report.auto_included.append(
                {"source": source, "file": img.filename}
            )


def _emit_single(ctx, category, source, img: CardImage, qty: int,
                 back: Optional[Path], match: str, note: str = "") -> None:
    ctx.report.entries.append(
        CardEntry(
            front=img.path,
            back=back,
            quantity=qty,
            name=img.name,
            number=img.number,
            category=category,
            double_sided=False,
            source=source,
            match=match,
            note=note,
        )
    )


# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #
def _group_by_number(images: list[CardImage]) -> "OrderedDict[str, list[CardImage]]":
    groups: "OrderedDict[str, list[CardImage]]" = OrderedDict()
    for img in images:
        groups.setdefault(img.number, []).append(img)
    return groups


def _apply_errata(images: list[CardImage], policy: str) -> list[CardImage]:
    """Collapse errata/non-errata duplicates that share the same name."""
    if policy == "both":
        return list(images)
    by_name: dict[str, list[CardImage]] = defaultdict(list)
    order: list[str] = []
    for img in images:
        key = normalize(img.name)
        if key not in by_name:
            order.append(key)
        by_name[key].append(img)

    result: list[CardImage] = []
    for key in order:
        group = by_name[key]
        if len(group) == 1:
            result.append(group[0])
            continue
        errata = [g for g in group if g.is_errata]
        plain = [g for g in group if not g.is_errata]
        if policy == "prefer" and errata:
            result.append(errata[0])
        elif policy == "skip" and plain:
            result.append(plain[0])
        else:
            result.extend(group)
    return result


def _candidate_map(images: list[CardImage], report: BuildReport) -> dict[str, CardImage]:
    candidates: dict[str, CardImage] = {}
    for img in images:
        key = normalize(img.name)
        candidates[key] = img
    return candidates


def _raw_back_image(folder: Optional[Path], name: str) -> Optional[CardImage]:
    """Find a back image by name among the folder's raw files, including files
    stored without a ``NNN -`` number prefix (e.g. a shared "Edge of the
    Temple.jpg")."""
    if folder is None:
        return None
    target = normalize(name)
    for p in sorted(folder.iterdir()):
        if p.is_file() and p.suffix.lower() in IMAGE_EXTS and normalize(p.stem) == target:
            return CardImage(path=p, number="", name=p.stem, is_errata=False,
                             side=None, stage=None)
    return None


def _pair_candidate_map(folder_pairs: list[tuple]) -> dict[str, CardEntry]:
    """Match keys for double-sided pairs: each side's name and both combined
    orders, so a cardlist 'SideA/SideB' entry resolves to the pair."""
    candidates: dict[str, CardEntry] = {}
    for entry, face, back in folder_pairs:
        for key in (normalize(face), normalize(back),
                    normalize(f"{face} {back}"), normalize(f"{back} {face}")):
            if key:
                candidates.setdefault(key, entry)
    return candidates


def _load_cardlist(folder: Path) -> Optional[list[tuple[int, str]]]:
    path = folder / "cardlist.txt"
    if not path.exists():
        return None
    entries: list[tuple[int, str]] = []
    for line in path.read_text(encoding="utf-8-sig").splitlines():
        if not line.strip():
            continue
        m = _CARDLIST_LINE.match(line)
        if m:
            entries.append((int(m.group(1)), m.group(2).strip()))
    return entries


def _rel_source(folder: Path, root: Path) -> str:
    try:
        rel = folder.relative_to(root)
        return str(rel) if str(rel) != "." else folder.name
    except ValueError:
        return folder.name
