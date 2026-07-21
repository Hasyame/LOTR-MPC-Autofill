"""Core data model for LOTRAutofill."""

from __future__ import annotations

from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Optional


# Category folder names as they appear on disk.
CATEGORY_ENCOUNTER = "Encounter"
CATEGORY_NIGHTMARE = "Nightmare"
CATEGORY_PLAYER = "Player"
CATEGORY_QUEST = "Quest"

CATEGORIES = (
    CATEGORY_ENCOUNTER,
    CATEGORY_NIGHTMARE,
    CATEGORY_PLAYER,
    CATEGORY_QUEST,
)

# Categories whose quantities come from a cardlist.txt file.
CARDLIST_CATEGORIES = (CATEGORY_ENCOUNTER, CATEGORY_NIGHTMARE)


@dataclass
class CardImage:
    """A single image file parsed from a category folder."""

    path: Path
    number: str          # zero-padded card number, e.g. "042"
    name: str            # human name without the "(errata)" suffix
    is_errata: bool
    side: Optional[str]  # "A" / "B" for quest cards, else None
    stage: Optional[str] # e.g. "1" / "2" / "3" for quest cards, else None

    @property
    def filename(self) -> str:
        return self.path.name


@dataclass
class CardEntry:
    """One resolved MPC slot: a front image, a back image and a quantity."""

    front: Path
    back: Optional[Path]
    quantity: int
    name: str
    number: str
    category: str
    double_sided: bool
    source: str                     # relative folder the card came from
    match: str = "exact"            # exact | fuzzy | none | implicit
    note: str = ""                  # free-form note (fuzzy target, warnings…)

    def to_dict(self, root: Path) -> dict:
        d = asdict(self)
        d["front"] = _rel(self.front, root)
        d["back"] = _rel(self.back, root) if self.back else None
        return d


@dataclass
class BuildReport:
    """Everything the build produced, for JSON export + human summary."""

    root: Path
    entries: list[CardEntry] = field(default_factory=list)
    unmatched_cardlist: list[dict] = field(default_factory=list)
    fuzzy_matches: list[dict] = field(default_factory=list)
    double_sided_pairs: list[dict] = field(default_factory=list)
    orphans: list[dict] = field(default_factory=list)
    auto_included: list[dict] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    @property
    def total_slots(self) -> int:
        return sum(e.quantity for e in self.entries)

    @property
    def unique_cards(self) -> int:
        return len(self.entries)


def _rel(p: Path, root: Path) -> str:
    try:
        return str(p.relative_to(root))
    except ValueError:
        return str(p)
