"""Network-free tests for the web GUI's set-image mapping and safety guards."""

from lotrautofill.webgui.server import _map_set_images, _product_image


def test_map_set_images_deluxe_and_cycle():
    products = [
        {"name": "Core Set", "image": "https://s3/Images/Products/MEC01.png"},
        {"name": "The Redhorn Gate", "image": "https://s3/Images/Products/MEC09.png"},
    ]
    sets = [
        {"name": "01 - Core Set", "display": "Core Set", "chapters": []},
        {"name": "04 - Dwarrowdelf", "display": "Dwarrowdelf", "chapters": [
            {"name": "01 - The Redhorn Gate", "display": "The Redhorn Gate"}]},
    ]
    _map_set_images(sets, products)
    assert sets[0]["image"] == "MEC01.png"                 # deluxe: direct match
    assert sets[1]["image"] == "MEC09.png"                 # cycle: first chapter
    assert sets[1]["chapters"][0]["image"] == "MEC09.png"


def test_product_image_rejects_unsafe_names():
    # Bad filenames are rejected before any network access (SSRF/path guard).
    assert _product_image("../../etc/passwd")[0] is None
    assert _product_image("evil.exe")[0] is None
    assert _product_image("")[0] is None
