"""Tests for set discovery, default library root, and the venv path helper."""

import os
from pathlib import Path

from lotrautofill.sets import discover_sets, default_library_root
from lotrautofill.upload.desktop_tool import _venv_python


def _make_set(root: Path, name: str, category: str = "Player") -> None:
    (root / name / name / category).mkdir(parents=True, exist_ok=True)
    (root / name / name / category / "001 - Card.jpg").write_bytes(b"")


def test_discover_sets_finds_card_folders(tmp_path):
    _make_set(tmp_path, "03 - Khazad-dum")
    _make_set(tmp_path, "19 - Hobbit")
    (tmp_path / "Card_Backs" / "Card_Backs").mkdir(parents=True)
    (tmp_path / "builds").mkdir()
    names = [p.name for p in discover_sets(tmp_path)]
    assert names == ["03 - Khazad-dum", "19 - Hobbit"]


def test_discover_sets_skips_non_card_dirs(tmp_path):
    (tmp_path / "random" / "sub").mkdir(parents=True)
    assert discover_sets(tmp_path) == []


def test_default_library_root_prefers_toprint(tmp_path):
    (tmp_path / "toPrint").mkdir()
    assert default_library_root(tmp_path).name == "toPrint"


def test_default_library_root_falls_back_to_dot(tmp_path):
    assert default_library_root(tmp_path) == tmp_path


def test_venv_python_path_is_os_specific(tmp_path):
    p = _venv_python(tmp_path / ".venv")
    if os.name == "nt":
        assert p.name == "python.exe" and p.parent.name == "Scripts"
    else:
        assert p.name == "python" and p.parent.name == "bin"
