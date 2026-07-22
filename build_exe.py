"""Build a standalone `lotr-autofill` executable with PyInstaller.

Usage:
    pip install -e .[build]      # installs pyinstaller
    python build_exe.py          # -> ./lotr-autofill(.exe) in the project root

Double-clicking the built .exe (no arguments) launches the web GUI and opens a
browser — the easiest way to run it. The Windows icon is Gandalf
(`lotrautofill/assets/gandalf.ico`). All subcommands still work from a terminal
(build / pick / export / sets / autofill / db / reference / gui). The optional
Playwright `upload` driver is
excluded to keep the binary small; the `autofill` command still shells out to a
real Python for the desktop tool. Pillow is bundled (if installed) so the GUI's
card thumbnails work; without it the GUI serves full images instead.
"""

from __future__ import annotations

import importlib.util
import os
import subprocess
import sys
from pathlib import Path

NAME = "lotr-autofill"
ENTRY = "pyinstaller_entry.py"


def main() -> int:
    root = Path(__file__).parent
    assets = root / "lotrautofill" / "assets"
    icon = assets / "gandalf.ico"
    # The bundled card database (copy counts + missing-card lists) must ride
    # along inside the exe so users only need to supply card images.
    card_db = root / "lotrautofill" / "catalog" / "data" / "cardlists.json"
    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--onefile",
        "--console",
        "--name", NAME,
        "--noconfirm",
        # Never UPX-pack: packed exes trip antivirus heuristics even harder.
        "--noupx",
        # Put the finished .exe in the project root (next to sets_folder), not
        # dist/ — clearer for users, and it finds the library right beside it.
        "--distpath", str(root),
        "--workpath", str(root / "build"),
        "--specpath", str(root),
        # Bundle every lotrautofill submodule (many are imported lazily in the
        # CLI handlers — library.*, catalog.*, mpc.*, web.*).
        "--collect-submodules", "lotrautofill",
        # Playwright is a heavy optional dep imported lazily; don't bundle it.
        "--exclude-module", "playwright",
    ]
    if card_db.is_file():
        cmd += ["--add-data",
                f"{card_db}{os.pathsep}lotrautofill/catalog/data"]
    if icon.is_file():
        cmd += ["--icon", str(icon)]  # Gandalf, the .exe's Windows icon only
    if importlib.util.find_spec("PIL") is not None:
        cmd += ["--hidden-import", "PIL.Image"]  # GUI thumbnails
    cmd.append(str(root / ENTRY))
    print("Running:", " ".join(cmd))
    result = subprocess.run(cmd)
    if result.returncode == 0:
        exe = root / (NAME + (".exe" if sys.platform == "win32" else ""))
        print(f"\nBuilt: {exe}")
    return result.returncode


if __name__ == "__main__":
    raise SystemExit(main())
