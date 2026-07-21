"""Parse a pasted decklist into ``(quantity, name)`` pairs.

Accepts one card per line in the common forms ``3x Gandalf``, ``3 Gandalf`` or
``Gandalf x3``; a trailing ``(Pack)`` and section headers/blank/comment lines
are ignored.
"""

from __future__ import annotations

import re

_LINE_LEADING = re.compile(r"^\s*(\d+)\s*[xX]?\s+(.+?)\s*$")
_LINE_TRAILING = re.compile(r"^\s*(.+?)\s*[xX]\s*(\d+)\s*$")
_TRAILING_PACK = re.compile(r"\s*\([^)]*\)\s*$")


def parse_decklist_text(text: str) -> list[tuple[int, str]]:
    entries: list[tuple[int, str]] = []
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        m = _LINE_LEADING.match(line)
        if m:
            qty, name = int(m.group(1)), m.group(2)
        else:
            m = _LINE_TRAILING.match(line)
            if not m:
                continue
            name, qty = m.group(1), int(m.group(2))
        name = _TRAILING_PACK.sub("", name).strip()
        if name:
            entries.append((qty, name))
    return entries
