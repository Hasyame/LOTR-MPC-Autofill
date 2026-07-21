"""Export an upload plan as an mpc-autofill order.xml (Local File mode).

Rather than driving MakePlayingCards ourselves, we produce the order file that
the proven `chilli-axe/mpc-autofill` desktop tool consumes. That tool already
handles the whole MPC browser automation robustly, and it supports local images:
if a card's ``<id>`` is a path that exists on disk, it is used directly as a
``Local File`` (no download).

Format (per the desktop tool's ``src/order.py``):

    <order>
      <details><quantity/><stock/><foil/></details>
      <fronts>  <card><id>PATH</id><slots>0,1,2</slots><name/></card> ... </fronts>
      <backs>   <card><id>PATH</id><slots>3</slots><name/></card>   ... </backs>
      <cardback>PATH</cardback>            <!-- default back for all other slots -->
    </order>

Slots are 0-indexed positions in deck order. The single most common back is
emitted as ``<cardback>`` (the tool's fast path); every other back goes in
``<backs>`` with just its slots.
"""

from __future__ import annotations

from collections import Counter, OrderedDict
from pathlib import Path
from typing import Optional
from xml.dom import minidom
from xml.etree import ElementTree as ET

from .config import DEFAULT_PRODUCT
from .plan import UploadPlan

# Cardstock strings accepted by the desktop tool (constants.Cardstocks).
VALID_STOCKS = {
    "(S27) Smooth",
    "(S30) Standard Smooth",
    "(S33) Superior Smooth",
    "(M31) Linen",
    "(P10) Plastic",
}


def plan_to_xml(
    plan: UploadPlan,
    stock: str = DEFAULT_PRODUCT.card_stock,
    foil: bool = False,
) -> str:
    if stock not in VALID_STOCKS:
        raise ValueError(f"Cardstock {stock!r} not supported by mpc-autofill "
                         f"(one of {sorted(VALID_STOCKS)})")

    order = ET.Element("order")

    details = ET.SubElement(order, "details")
    ET.SubElement(details, "quantity").text = str(plan.total_cards)
    ET.SubElement(details, "stock").text = stock
    ET.SubElement(details, "foil").text = "true" if foil else "false"

    # Fronts: group slot indices by front image path (first-seen order).
    front_slots: "OrderedDict[Path, list[int]]" = OrderedDict()
    for i, slot in enumerate(plan.slots):
        if slot.front is not None:
            front_slots.setdefault(slot.front, []).append(i)
    _append_cards(ET.SubElement(order, "fronts"), front_slots)

    # Pick the most common back as the default cardback (tool fast-path).
    back_counter: Counter[Path] = Counter(
        slot.back for slot in plan.slots if slot.back is not None
    )
    default_back: Optional[Path] = (
        back_counter.most_common(1)[0][0] if back_counter else None
    )

    # Backs: only slots whose back differs from the default cardback.
    back_slots: "OrderedDict[Path, list[int]]" = OrderedDict()
    for i, slot in enumerate(plan.slots):
        if slot.back is not None and slot.back != default_back:
            back_slots.setdefault(slot.back, []).append(i)
    _append_cards(ET.SubElement(order, "backs"), back_slots)

    if default_back is not None:
        ET.SubElement(order, "cardback").text = str(default_back)

    return _pretty(order)


def _append_cards(parent: ET.Element, by_path: "OrderedDict[Path, list[int]]") -> None:
    for path, slots in by_path.items():
        card = ET.SubElement(parent, "card")
        ET.SubElement(card, "id").text = str(path)
        ET.SubElement(card, "slots").text = ",".join(str(s) for s in slots)
        ET.SubElement(card, "name").text = path.name


def _pretty(elem: ET.Element) -> str:
    raw = ET.tostring(elem, encoding="unicode")
    return minidom.parseString(raw).toprettyxml(indent="    ")
