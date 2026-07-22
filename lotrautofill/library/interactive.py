"""Interactive prompts for resolving ambiguous cards.

Every prompt has a default so that non-interactive runs (no TTY, ``--yes``,
or EOF on stdin) resolve to sensible values without blocking.
"""

from __future__ import annotations

import sys


class Prompter:
    def __init__(self, enabled: bool):
        self.enabled = enabled

    def choose(self, question: str, labels: list[str], default: int = 0) -> int:
        """Ask the user to pick one option; return its index.

        Falls back to ``default`` when disabled or on EOF/invalid input.
        """
        if not self.enabled or not labels:
            return default

        print(f"\n{question}")
        for i, label in enumerate(labels):
            marker = "*" if i == default else " "
            print(f"  {marker}[{i + 1}] {label}")
        try:
            raw = input(f"Choice [1-{len(labels)}] (default {default + 1}): ").strip()
        except EOFError:
            return default
        if not raw:
            return default
        if raw.isdigit():
            idx = int(raw) - 1
            if 0 <= idx < len(labels):
                return idx
        print("  (invalid — using default)")
        return default

    def confirm(self, question: str, default: bool = True) -> bool:
        if not self.enabled:
            return default
        suffix = "[Y/n]" if default else "[y/N]"
        try:
            raw = input(f"{question} {suffix}: ").strip().lower()
        except EOFError:
            return default
        if not raw:
            return default
        return raw in ("y", "yes", "o", "oui")


def default_enabled() -> bool:
    """Interactive by default only when stdin is a real terminal."""
    try:
        return sys.stdin.isatty()
    except (AttributeError, ValueError):
        return False
