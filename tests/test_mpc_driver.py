"""Tests for the Playwright driver's browser-free helpers."""

import hashlib

from lotrautofill.upload.plan import plan_from_manifest
from lotrautofill.upload.mpc import _pid, _slots_by_image


def _plan(tmp):
    for n in ("f1.jpg", "f2.jpg", "encback.jpg", "qback.jpg"):
        (tmp / n).write_bytes(n.encode())
    manifest = {
        "root": str(tmp),
        "cards": [
            {"front": "f1.jpg", "back": "encback.jpg", "quantity": 2,
             "name": "A", "category": "Encounter"},
            {"front": "f2.jpg", "back": "qback.jpg", "quantity": 1,
             "name": "B", "category": "Quest", "double_sided": True},
        ],
    }
    return plan_from_manifest(manifest)


def test_slots_by_image_fronts(tmp_path):
    plan = _plan(tmp_path)
    fronts = _slots_by_image(plan, face="front")
    by_name = {p.name: slots for p, slots in fronts.items()}
    assert by_name["f1.jpg"] == [0, 1]      # 2 copies -> slots 0,1
    assert by_name["f2.jpg"] == [2]


def test_slots_by_image_backs(tmp_path):
    plan = _plan(tmp_path)
    backs = _slots_by_image(plan, face="back")
    by_name = {p.name: slots for p, slots in backs.items()}
    assert by_name["encback.jpg"] == [0, 1]
    assert by_name["qback.jpg"] == [2]


def test_pid_is_uppercase_sha1(tmp_path):
    f = tmp_path / "x.jpg"
    f.write_bytes(b"hello")
    assert _pid(f) == hashlib.sha1(b"hello").hexdigest().upper()
