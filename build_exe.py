"""Build a standalone `lotr-autofill` executable with PyInstaller.

Usage:
    pip install -e .[build]      # installs pyinstaller
    python build_exe.py          # -> dist/lotr-autofill(.exe)

The executable bundles the whole CLI (build / pick / export / sets / autofill /
db / reference / gui). The optional Playwright `upload` driver is
excluded to keep the binary small; the `autofill` command still shells out to a
real Python for the desktop tool. Pillow is bundled (if installed) so the GUI's
card thumbnails work; without it the GUI serves full images instead.
"""

from __future__ import annotations

import importlib.util
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
        # Bundle every lotrautofill submodule (many are imported lazily in the
        # CLI handlers — library.*, catalog.*, mpc.*, web.*).
        "--collect-submodules", "lotrautofill",
        # Playwright is a heavy optional dep imported lazily; don't bundle it.
        "--exclude-module", "playwright",
    ]
    if importlib.util.find_spec("PIL") is not None:
        cmd += ["--hidden-import", "PIL.Image"]  # GUI thumbnails
    cmd.append(str(root / ENTRY))
    print("Running:", " ".join(cmd))
    result = subprocess.run(cmd)
    if result.returncode == 0:
        exe = root / "dist" / (NAME + (".exe" if sys.platform == "win32" else ""))
        print(f"\nBuilt: {exe}")
    return result.returncode


if __name__ == "__main__":
    raise SystemExit(main())
