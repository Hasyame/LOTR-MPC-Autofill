"""Discover printable set folders under a root directory."""

from __future__ import annotations

import re
from pathlib import Path

from .model import CATEGORIES

EXCLUDE_NAMES = {"Card_Backs", "MPC_XML", "builds", "sets_folder", "toPrint",
                 "__pycache__"}

# Card libraries live in one of these folders by convention (git-ignored).
# "sets_folder" is current; "toPrint" is accepted for backward compatibility.
LIBRARY_DIRNAMES = ("sets_folder", "toPrint")
# Generated order.xml files are written here.
OUTPUT_DIRNAME = "MPC_XML"


_NUM_PREFIX = re.compile(r"^\d+\s*-\s*")


def display_name(name: str) -> str:
    """A set/chapter name for display: the ``NN - `` ordering prefix removed."""
    return _NUM_PREFIX.sub("", name)


def default_library_root(cwd: Path | None = None) -> Path:
    """Where to look for sets by default: ``sets_folder/`` (or ``toPrint/``) if
    present, else the current directory."""
    base = Path(cwd) if cwd else Path(".")
    for name in LIBRARY_DIRNAMES:
        candidate = base / name
        if candidate.is_dir():
            return candidate
    return base


def discover_sets(root: Path) -> list[Path]:
    """Immediate sub-folders of ``root`` that contain LOTR cards.

    A folder qualifies if a category folder (Encounter/Player/Quest/Nightmare)
    appears somewhere inside it. ``Card_Backs`` and build output are skipped.
    """
    root = Path(root)
    found: list[Path] = []
    for child in sorted(p for p in root.iterdir() if p.is_dir()):
        if child.name in EXCLUDE_NAMES:
            continue
        if _contains_category(child):
            found.append(child)
    return found


def _contains_category(folder: Path) -> bool:
    for p in folder.rglob("*"):
        if p.is_dir() and p.name in CATEGORIES:
            return True
    return False


def _has_direct_category(folder: Path) -> bool:
    return any((folder / cat).is_dir() for cat in CATEGORIES)


def discover_chapters(set_folder: Path) -> list[Path]:
    """Chapter folders inside a set, or ``[]`` if the set has no chapters.

    A "category container" is any folder that *directly* holds Encounter/Player/
    Quest/Nightmare sub-folders. A set with chapters (e.g. a saga) has several
    such containers — one per chapter; a plain box has exactly one (the set
    itself), so we report no chapters there.
    """
    containers = [
        p for p in sorted(Path(set_folder).rglob("*"))
        if p.is_dir() and _has_direct_category(p)
    ]
    return containers if len(containers) > 1 else []
