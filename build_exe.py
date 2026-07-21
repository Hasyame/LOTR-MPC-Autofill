"""Build a standalone `lotr-autofill` executable with PyInstaller.

Usage:
    pip install -e .[build]      # installs pyinstaller
    python build_exe.py          # -> dist/lotr-autofill(.exe)

The executable bundles the CLI (build / pick / export / sets / autofill). The
optional Playwright `upload` driver is excluded to keep the binary small; the
`autofill` command still shells out to a real Python for the desktop tool.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

NAME = "lotr-autofill"
ENTRY = "pyinstaller_entry.py"


def main() -> int:
    root = Path(__file__).parent
    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--onefile",
        "--console",
        "--name", NAME,
        "--noconfirm",
        # Playwright is a heavy optional dep imported lazily; don't bundle it.
        "--exclude-module", "playwright",
        str(root / ENTRY),
    ]
    print("Running:", " ".join(cmd))
    result = subprocess.run(cmd)
    if result.returncode == 0:
        exe = root / "dist" / (NAME + (".exe" if sys.platform == "win32" else ""))
        print(f"\nBuilt: {exe}")
    return result.returncode


if __name__ == "__main__":
    raise SystemExit(main())
