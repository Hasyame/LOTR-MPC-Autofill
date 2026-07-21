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

# Upload + per-slot insert mechanism (ported from mpc-autofill's src/driver.py).
# The hidden file input; send a local path to it to upload one image.
SEL_UPLOAD_INPUT = "#uploadId"
# Loading spinner shown while the editor processes an action.
SEL_WAIT_SPINNER = "#sysdiv_wait"
# A popup close button that can appear when paging to backs.
SEL_CLOSE_BTN = "#closeBtn"
# "Accept settings" URL that doPersonalize() loads to enter the editor.
ACCEPT_SETTINGS_URL = EDITOR_URL

# JS the editor exposes (top-level page unless noted):
#   oDesignImage.UploadStatus == 'Uploading'      -> an upload is in progress
#   oDesignImage.dn_getImageList()                -> ';'-joined pids of uploads
#   PageLayout.prototype.getElement3("dnImg", n)  -> the slot-n card element
#   PageLayout.prototype.applyDragPhoto(el, 0, p) -> place image pid p in slot
#   oDesign.setNextStep() / oDesign.setTemporarySave()
#   setMode('ImageText', 0|1)  (inside #sysifm_loginFrame) -> different|same img
JS_NEXT_STEP = "oDesign.setNextStep();"
JS_SET_DIFFERENT_IMAGES = "setMode('ImageText', 0);"
JS_SET_SAME_IMAGE = "setMode('ImageText', 1);"

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
