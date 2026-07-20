"""Name normalization and fuzzy matching between cardlist entries and files."""

from __future__ import annotations

import re
from difflib import SequenceMatcher

# Apostrophes and their filename placeholder ("_") are dropped entirely so that
# "Thror's Map" (cardlist) and "Thror_s Map" (filename) normalize identically.
_APOSTROPHES = re.compile(r"[_'’`´]")
_NON_ALNUM = re.compile(r"[^a-z0-9]+")
_WS = re.compile(r"\s+")

# Similarity threshold for accepting a fuzzy (typo-tolerant) match.
FUZZY_CUTOFF = 0.72


def normalize(name: str) -> str:
    """Normalize a card name for robust matching.

    Lowercases, removes apostrophes/underscores, turns any other punctuation
    into spaces, and collapses whitespace.
    """
    s = name.lower()
    s = _APOSTROPHES.sub("", s)
    s = _NON_ALNUM.sub(" ", s)
    s = _WS.sub(" ", s).strip()
    return s


def similarity(a: str, b: str) -> float:
    return SequenceMatcher(None, a, b).ratio()


def best_match(query: str, candidates: dict[str, object]) -> tuple[object | None, str, float]:
    """Match a cardlist name against candidate images.

    ``candidates`` maps normalized-name -> value. Returns
    ``(value, kind, score)`` where kind is "exact", "fuzzy" or "none".
    """
    q = normalize(query)
    if q in candidates:
        return candidates[q], "exact", 1.0

    best_key: str | None = None
    best_score = 0.0
    for key in candidates:
        score = similarity(q, key)
        if score > best_score:
            best_score = score
            best_key = key

    if best_key is not None and best_score >= FUZZY_CUTOFF:
        return candidates[best_key], "fuzzy", best_score
    return None, "none", best_score
