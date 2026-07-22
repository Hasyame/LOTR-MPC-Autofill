"""Turn a build manifest into an ordered MPC upload plan.

A plan is what the browser driver needs, decoupled from how the site works:

* ``slots`` — the deck in order, one entry per physical card (quantities
  expanded). Each slot has a front image and a back image.
* ``unique_fronts`` / ``unique_backs`` — each distinct image file, once, in
  first-seen order (MPC uploads each image a single time, then references it).
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from .config import MPC_MAX_CARDS_PER_PROJECT  # re-exported for callers


@dataclass
class Slot:
    front: Path
    back: Optional[Path]
    name: str
    category: str


@dataclass
class UploadPlan:
    slots: list[Slot]
    unique_fronts: list[Path]
    unique_backs: list[Path]
    missing_files: list[Path]

    @property
    def total_cards(self) -> int:
        return len(self.slots)

    @property
    def exceeds_project_limit(self) -> bool:
        return self.total_cards > MPC_MAX_CARDS_PER_PROJECT


def load_manifest(path: Path) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def plan_from_manifest(manifest: dict, root: Optional[Path] = None) -> UploadPlan:
    base = Path(root) if root else Path(manifest.get("root", "."))
    slots: list[Slot] = []
    fronts: list[Path] = []
    backs: list[Path] = []
    seen_front: set[Path] = set()
    seen_back: set[Path] = set()
    missing: list[Path] = []
    seen_missing: set[Path] = set()

    def resolve(rel: Optional[str]) -> Optional[Path]:
        if not rel:
            return None
        p = Path(rel)
        if not p.is_absolute():
            p = base / p
        if not p.exists() and p not in seen_missing:
            seen_missing.add(p)
            missing.append(p)
        return p

    for card in manifest.get("cards", []):
        front = resolve(card.get("front"))
        back = resolve(card.get("back"))
        qty = int(card.get("quantity", 1))
        if front is not None and front not in seen_front:
            seen_front.add(front)
            fronts.append(front)
        if back is not None and back not in seen_back:
            seen_back.add(back)
            backs.append(back)
        for _ in range(qty):
            slots.append(
                Slot(
                    front=front,
                    back=back,
                    name=card.get("name", ""),
                    category=card.get("category", ""),
                )
            )

    return UploadPlan(
        slots=slots,
        unique_fronts=fronts,
        unique_backs=backs,
        missing_files=missing,
    )
