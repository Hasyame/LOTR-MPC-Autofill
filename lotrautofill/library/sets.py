"""Discover printable set folders under a root directory."""

from __future__ import annotations

import re
import sys
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


def _default_bases() -> list[Path]:
    """Directories to search for a library folder, most-preferred first.

    As a frozen executable the folder next to the ``.exe`` comes first: that is
    where users drop ``sets_folder`` next to the double-clickable app, and a
    double-clicked / "Run as administrator" exe often starts with the working
    directory pointing elsewhere (e.g. System32). The working directory is
    always searched too, so running from a terminal keeps working.
    """
    bases: list[Path] = []
    if getattr(sys, "frozen", False):
        bases.append(Path(sys.executable).resolve().parent)
    bases.append(Path("."))
    return bases


def default_library_root(cwd: Path | None = None) -> Path:
    """Where to look for sets by default: ``sets_folder/`` (or ``toPrint/``) if
    present, else the base directory. An explicit ``cwd`` is used verbatim;
    otherwise the .exe folder (when frozen) and the working directory are
    searched in that order."""
    bases = [Path(cwd)] if cwd is not None else _default_bases()
    for base in bases:
        for name in LIBRARY_DIRNAMES:
            candidate = base / name
            if candidate.is_dir():
                return candidate
    return bases[0]


def default_output_dir() -> Path:
    """Where generated ``order.xml`` files go by default: ``MPC_XML/`` next to
    the .exe when frozen (the working directory may be unwritable, e.g.
    System32 for a double-clicked/admin-launched exe), else under the working
    directory."""
    base = Path(sys.executable).resolve().parent \
        if getattr(sys, "frozen", False) else Path(".")
    return base / OUTPUT_DIRNAME


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
