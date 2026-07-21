"""Tests for set discovery, default library root, and the venv path helper."""

import os
from pathlib import Path

from lotrautofill.sets import (
    default_library_root,
    discover_chapters,
    discover_sets,
    display_name,
)
from lotrautofill.upload.desktop_tool import _venv_python


def _make_set(root: Path, name: str, category: str = "Player") -> None:
    (root / name / name / category).mkdir(parents=True, exist_ok=True)
    (root / name / name / category / "001 - Card.jpg").write_bytes(b"")


def _make_chaptered_set(root: Path, name: str, chapters: list[str]) -> Path:
    for ch in chapters:
        cat = root / name / name / ch / "Player"
        cat.mkdir(parents=True, exist_ok=True)
        (cat / "001 - Card.jpg").write_bytes(b"")
    return root / name


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


def test_sets_found_with_or_without_number_prefix(tmp_path):
    _make_set(tmp_path, "Core Set")            # English name, no number
    _make_set(tmp_path, "07 - The Voice of Isengard")  # numbered
    names = [p.name for p in discover_sets(tmp_path)]
    assert "Core Set" in names and "07 - The Voice of Isengard" in names


def test_display_name_strips_optional_number_prefix():
    assert display_name("03 - Khazad-dûm") == "Khazad-dûm"
    assert display_name("Core Set") == "Core Set"


def test_default_library_root_prefers_toprint(tmp_path):
    (tmp_path / "toPrint").mkdir()
    assert default_library_root(tmp_path).name == "toPrint"


def test_default_library_root_falls_back_to_dot(tmp_path):
    assert default_library_root(tmp_path) == tmp_path


def test_chapters_detected_for_saga(tmp_path):
    s = _make_chaptered_set(tmp_path, "19 - Saga",
                            ["01 - First", "02 - Second"])
    names = [c.name for c in discover_chapters(s)]
    assert names == ["01 - First", "02 - Second"]


def test_no_chapters_for_plain_box(tmp_path):
    _make_set(tmp_path, "03 - Box")
    assert discover_chapters(tmp_path / "03 - Box") == []


def test_venv_python_path_is_os_specific(tmp_path):
    p = _venv_python(tmp_path / ".venv")
    if os.name == "nt":
        assert p.name == "python.exe" and p.parent.name == "Scripts"
    else:
        assert p.name == "python" and p.parent.name == "bin"
