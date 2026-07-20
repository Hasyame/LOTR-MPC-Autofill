"""MakePlayingCards product configuration + DOM selectors for the order.

Values and selectors were captured from the live MPC "blank poker cards"
product page. The card-stock/deck-size/etc. controls are native ``<select>``
elements, so we drive them by their stable option *values*.
"""

from __future__ import annotations

from dataclasses import dataclass

# Product landing page (blank, poker size 2.5"x3.5", rounded corner, full bleed).
PRODUCT_URL = (
    "https://www.makeplayingcards.com/design/custom-white-border-poker-sized-cards.html"
)
CART_URL = "https://www.makeplayingcards.com/cart/cart.aspx"

# The "Start your design" link calls doPersonalize(...) which loads this editor.
EDITOR_URL = "https://www.makeplayingcards.com/products/pro_item_process_flow.aspx"

# --- Config-page <select> element ids (captured live) ------------------------
SEL_CARD_STOCK = "#dro_paper_type"
SEL_DECK_SIZE = "#dro_choosesize"
SEL_PRINT_TYPE = "#dro_product_effect"
SEL_FINISH = "#dro_product_process_PPN_0001"
SEL_PACKAGING = "#dro_packoption"
# "Start your design" link (calls doPersonalize -> EDITOR_URL).
TXT_START_DESIGN = "Start your design"

# --- Editor flow (captured live) --------------------------------------------
# EDITOR_URL loads an iframe (#sysifm_loginFrame) = dn_playingcards_mode_nf.aspx
# holding "Step 1: number of cards / packaging".
FRAME_EDITOR = "#sysifm_loginFrame"
SEL_STEP1_CARD_NUMBER = "#txt_card_number"   # actual card count (<= deck tier)
SEL_STEP1_DECK_TOTAL = "#dro_total_count"
SEL_STEP1_PACKAGING = "#dro_packoption"
# Proceeding uses the PARENT-level button (not the one inside the iframe).
SEL_NEXT_STEP = "#btn_next_step"             # onclick __doPostBack('btn_next_step','')

# Design app exposes JS globals `oDesign` (177 methods) and `oTrackerBar`.
# Front-image customization (upload + AUTOFILL) lives on this page; ssid is the
# project id parsed from the editor URL. Reached via "Customize Front" tab or:
FRONT_DYNAMIC_URL = (
    "https://www.makeplayingcards.com/products/playingcard/design/"
    "dn_playingcards_front_dynamic.aspx?ssid={ssid}"
)
BACK_DYNAMIC_URL = (
    "https://www.makeplayingcards.com/products/playingcard/design/"
    "dn_playingcards_back_dynamic.aspx?ssid={ssid}"
)

# Confirmed JS hooks on the front/back dynamic pages (logged in):
#   oDesign.applyPopupPhoto()     -> opens the photo/upload popup
#   oDesign.setAutoFill()         -> autofills uploaded images into slots
#   oDesign.setAutoFillHandle()   -> autofill (handle variant)
#   oDesign.setNextStep()         -> advance the flow
JS_OPEN_UPLOAD = "oDesign.applyPopupPhoto();"
JS_AUTOFILL = "oDesign.setAutoFill();"
JS_NEXT_STEP = "oDesign.setNextStep();"
# TODO (confirm during a local headed run): the file <input type=file> selector
# inside the photo popup, and the popup's "add to project / done" control. The
# popup renders async in a canvas editor, so it needs a visible run to capture.

# MPC "size of deck" tiers (max cards billed per deck). Pick the smallest >= n.
DECK_SIZE_TIERS = [18, 36, 55, 72, 90, 108, 126, 144, 162, 180, 198, 216, 234,
                   396, 504, 612]
MPC_MAX_CARDS_PER_PROJECT = DECK_SIZE_TIERS[-1]  # 612


def deck_size_tier(card_count: int) -> int:
    """Smallest MPC deck-size tier that holds ``card_count`` cards."""
    for tier in DECK_SIZE_TIERS:
        if card_count <= tier:
            return tier
    raise ValueError(
        f"{card_count} cards exceeds the largest MPC deck ({MPC_MAX_CARDS_PER_PROJECT})"
    )


@dataclass
class MpcProductConfig:
    product: str = "Blank poker cards (custom face & back)"
    size: str = '2.5" x 3.5" (63.5mm x 89mm)'
    # Card stock: option label + <select> value.
    card_stock: str = "(S33) Superior Smooth"
    card_stock_value: str = "PA_060"
    # Defaults observed on the product page (user may override later).
    print_type: str = "Full color print"
    finish: str = "MPC game card finish"       # value PPR_0011
    finish_value: str = "PPR_0011"
    packaging: str = "Shrink-wrapped"           # value PB_004
    packaging_value: str = "PB_004"

    def deck_size_for(self, card_count: int) -> int:
        return deck_size_tier(card_count)


DEFAULT_PRODUCT = MpcProductConfig()
