"""Minimal zero-dependency test runner (also works under pytest).

Discovers ``test_*`` functions in ``tests/`` and injects a ``tmp_path``
(temporary directory) when a test asks for it. Run: ``python run_tests.py``.
"""

from __future__ import annotations

import importlib
import inspect
import sys
import tempfile
import traceback
from pathlib import Path

TESTS_DIR = Path(__file__).parent / "tests"


def main() -> int:
    sys.path.insert(0, str(TESTS_DIR))
    sys.path.insert(0, str(Path(__file__).parent))

    passed = failed = 0
    for file in sorted(TESTS_DIR.glob("test_*.py")):
        module = importlib.import_module(file.stem)
        for name, fn in sorted(inspect.getmembers(module, inspect.isfunction)):
            if not name.startswith("test_"):
                continue
            try:
                if "tmp_path" in inspect.signature(fn).parameters:
                    with tempfile.TemporaryDirectory() as d:
                        fn(Path(d))
                else:
                    fn()
                passed += 1
            except Exception:
                failed += 1
                print(f"FAIL {file.stem}.{name}")
                traceback.print_exc()

    print(f"\n{passed} passed, {failed} failed")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
