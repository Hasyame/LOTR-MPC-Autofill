"""Discover printable set folders under a root directory."""

from __future__ import annotations

from pathlib import Path

from .model import CATEGORIES

EXCLUDE_NAMES = {"Card_Backs", "builds", "toPrint", "__pycache__"}

# Card libraries live here by convention (git-ignored).
LIBRARY_DIRNAME = "toPrint"


def default_library_root(cwd: Path | None = None) -> Path:
    """Where to look for sets by default: ``toPrint/`` if it exists, else ``.``."""
    base = Path(cwd) if cwd else Path(".")
    candidate = base / LIBRARY_DIRNAME
    return candidate if candidate.is_dir() else base


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
