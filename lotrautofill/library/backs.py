"""Locate the shared card-back images (Card_Backs folder)."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Optional

ENCOUNTER_BACK = "Encounter Card Back.jpg"
PLAYER_BACK = "Player Card Back.jpg"
_IMAGE_EXTS = {".jpg", ".jpeg", ".png"}


@dataclass(frozen=True)
class BackChoice:
    label: str
    path: Path


class CardBacks:
    """Resolves the common back image for a given card category.

    Also exposes every available back image so callers can offer the user a
    choice of which back (or face) to use.
    """

    def __init__(self, backs_dir: Optional[Path]):
        self.backs_dir = backs_dir
        self.encounter: Optional[Path] = None
        self.player: Optional[Path] = None
        self.choices: list[BackChoice] = []
        if backs_dir is not None:
            enc = backs_dir / ENCOUNTER_BACK
            ply = backs_dir / PLAYER_BACK
            self.encounter = enc if enc.exists() else None
            self.player = ply if ply.exists() else None
            self.choices = self._list_choices(backs_dir)

    @staticmethod
    def _list_choices(backs_dir: Path) -> list[BackChoice]:
        choices: list[BackChoice] = []
        for p in sorted(backs_dir.iterdir()):
            if p.is_file() and p.suffix.lower() in _IMAGE_EXTS:
                choices.append(BackChoice(label=p.stem, path=p))
        return choices

    def for_category(self, category: str) -> Optional[Path]:
        from .model import CATEGORY_PLAYER

        if category == CATEGORY_PLAYER:
            return self.player
        return self.encounter


def find_backs_dir(start: Path) -> Optional[Path]:
    """Search ``start`` and its parents for a ``Card_Backs`` folder holding backs.

    The observed layout nests the images one level deeper
    (``Card_Backs/Card_Backs/*.jpg``), so we return whichever level actually
    contains the back images.
    """
    current = start.resolve()
    for base in (current, *current.parents):
        candidate = base / "Card_Backs"
        if candidate.is_dir():
            return _resolve_backs_level(candidate)
    return None


def _resolve_backs_level(folder: Path) -> Path:
    if (folder / ENCOUNTER_BACK).exists() or (folder / PLAYER_BACK).exists():
        return folder
    nested = folder / folder.name
    if nested.is_dir() and (
        (nested / ENCOUNTER_BACK).exists() or (nested / PLAYER_BACK).exists()
    ):
        return nested
    subdirs = [p for p in folder.iterdir() if p.is_dir()]
    if len(subdirs) == 1:
        return subdirs[0]
    return folder
