"""Entry point for the standalone `lotr-autofill` executable (PyInstaller)."""

import sys

from lotrautofill.cli import main

if __name__ == "__main__":
    sys.exit(main())
