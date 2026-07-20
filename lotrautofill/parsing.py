"""Parse card image filenames and locate category folders on disk."""

from __future__ import annotations

import re
from pathlib import Path

from .model import CardImage, CATEGORIES

IMAGE_EXTS = {".jpg", ".jpeg", ".png"}

# "042 - Great Cave-troll"           -> number 042,          name "Great Cave-troll"
# "003 - Nori (errata)"              -> number 003, errata,  name "Nori"
# "023 - 1A - An Unexpected Party"   -> number 023, side A,  stage 1, name "An Unexpected Party"
_ERRATA_RE = re.compile(r"\s*\(errata\)\s*$", re.IGNORECASE)
_STAGE_RE = re.compile(r"^(\d+)([AB])$", re.IGNORECASE)
_NUMBER_RE = re.compile(r"^\d+[A-Za-z]?$")


def parse_filename(path: Path) -> CardImage | None:
    """Parse a ``NNN - [stage] - Name`` image filename into a CardImage."""
    stem = path.stem
    parts = [p.strip() for p in stem.split(" - ")]
    if len(parts) < 2 or not _NUMBER_RE.match(parts[0]):
        return None

    number = parts[0]
    side: str | None = None
    stage: str | None = None

    rest = parts[1:]
    m = _STAGE_RE.match(rest[0]) if rest else None
    if m and len(rest) >= 2:
        stage = m.group(1)
        side = m.group(2).upper()
        name = " - ".join(rest[1:])
    else:
        name = " - ".join(rest)

    is_errata = bool(_ERRATA_RE.search(name))
    name = _ERRATA_RE.sub("", name).strip()

    return CardImage(
        path=path,
        number=number,
        name=name,
        is_errata=is_errata,
        side=side,
        stage=stage,
    )


def list_images(folder: Path) -> list[CardImage]:
    """Return parsed CardImages for every image file directly in ``folder``."""
    images: list[CardImage] = []
    for p in sorted(folder.iterdir()):
        if p.is_file() and p.suffix.lower() in IMAGE_EXTS:
            card = parse_filename(p)
            if card is not None:
                images.append(card)
    return images


def find_category_folders(root: Path) -> list[tuple[str, Path]]:
    """Recursively find (category, folder) pairs under ``root``.

    A category is any folder named Encounter/Nightmare/Player/Quest. For
    Encounter/Nightmare the images live in sub-folders (one per encounter set);
    for Player/Quest the images live directly in the category folder.
    """
    found: list[tuple[str, Path]] = []
    for p in sorted(root.rglob("*")):
        if p.is_dir() and p.name in CATEGORIES:
            found.append((p.name, p))
    # Also handle the case where ``root`` itself is a category folder.
    if root.name in CATEGORIES:
        found.insert(0, (root.name, root))
    return found


def image_folders_for_category(category: str, folder: Path) -> list[Path]:
    """Folders that actually contain images for a category.

    Encounter/Nightmare group images in per-set sub-folders; Player/Quest hold
    images directly. We support both by returning any folder (self or child)
    that directly contains at least one image file.
    """
    folders: list[Path] = []
    if _has_images(folder):
        folders.append(folder)
    for child in sorted(folder.iterdir()):
        if child.is_dir() and _has_images(child):
            folders.append(child)
    return folders


def _has_images(folder: Path) -> bool:
    return any(
        p.is_file() and p.suffix.lower() in IMAGE_EXTS for p in folder.iterdir()
    )
