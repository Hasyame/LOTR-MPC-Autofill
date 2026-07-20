"""Playwright driver for MakePlayingCards (stage 2).

Target product: blank poker cards (custom face & back), size 2.5"x3.5", up to
612 cards per deck.

Flow captured from the live site:
  1. product page  -> select card stock / deck size / packaging
  2. "Start your design" (doPersonalize) -> editor
  3. editor Step 1 (iframe #sysifm_loginFrame): #txt_card_number, then the
     PARENT #btn_next_step
  4. front page dn_playingcards_front_dynamic.aspx exposes JS hooks
     oDesign.applyPopupPhoto() (upload popup) and oDesign.setAutoFill()
  5. back assignment, then stop at the cart

Signing in and the async photo popup's file-input selector are handled in a
supervised, visible run: the driver pauses so the operator signs in and (until
the popup selector is confirmed locally) performs the image upload, then the
driver calls the confirmed autofill hook. It never places the order.
"""

from __future__ import annotations

from pathlib import Path

from . import config as cfg
from .config import DEFAULT_PRODUCT, MpcProductConfig
from .plan import UploadPlan


class MpcDriver:
    def __init__(self, headed: bool = True, slow_mo_ms: int = 0,
                 product: MpcProductConfig = DEFAULT_PRODUCT):
        self.headed = headed
        self.slow_mo_ms = slow_mo_ms
        self.product = product
        self._browser = None
        self._page = None
        self._pw = None

    # ---- lifecycle ------------------------------------------------------- #
    def _launch(self):
        from playwright.sync_api import sync_playwright  # lazy import

        self._pw = sync_playwright().start()
        self._browser = self._pw.chromium.launch(
            headless=not self.headed, slow_mo=self.slow_mo_ms
        )
        self._page = self._browser.new_context().new_page()

    def close(self) -> None:
        if self._browser:
            self._browser.close()
        if self._pw:
            self._pw.stop()

    # ---- high-level flow ------------------------------------------------- #
    def fill_order(self, plan: UploadPlan) -> int:
        if plan.missing_files:
            print(f"Refusing to start: {len(plan.missing_files)} image(s) missing.")
            return 4
        try:
            tier = self.product.deck_size_for(plan.total_cards)
        except ValueError as exc:
            print(f"{exc}\nSplit the manifest into multiple orders.")
            return 5

        self._launch()
        try:
            self._require_login()
            self._configure_product(tier)
            self._editor_step1(plan.total_cards)
            self._customize_fronts(plan.unique_fronts)
            self._assign_backs(plan)
            self._go_to_cart()

            print("\nStopped at the cart. Review and pay manually in the browser.")
            self._pause("Press Enter to close the browser...")
            return 0
        finally:
            self.close()

    # ---- login (operator types credentials; driver never does) ----------- #
    def _require_login(self) -> None:
        self._page.goto("https://www.makeplayingcards.com/login.aspx",
                        wait_until="domcontentloaded")
        print("Sign in to your MPC account in the opened window.")
        self._pause("Press Enter once you are signed in...")

    # ---- product configuration (wired to live selectors) ----------------- #
    def _configure_product(self, deck_tier: int) -> None:
        page = self._page
        p = self.product
        print(f"Opening product page: {cfg.PRODUCT_URL}")
        page.goto(cfg.PRODUCT_URL, wait_until="domcontentloaded")
        self._reject_cookies()

        print(f"  card stock -> {p.card_stock}")
        page.select_option(cfg.SEL_CARD_STOCK, value=p.card_stock_value)
        print(f"  deck size  -> Up to {deck_tier} cards")
        page.select_option(cfg.SEL_DECK_SIZE, value=str(deck_tier))
        if page.locator(cfg.SEL_PACKAGING).count():
            page.select_option(cfg.SEL_PACKAGING, value=p.packaging_value)

        print("  starting design editor...")
        page.get_by_text(cfg.TXT_START_DESIGN, exact=False).first.click()
        page.wait_for_load_state("domcontentloaded")

    def _reject_cookies(self) -> None:
        try:
            self._page.get_by_role("link", name="Reject").click(timeout=3000)
        except Exception:
            pass

    # ---- editor Step 1: number of cards (inside the iframe) -------------- #
    def _editor_step1(self, card_count: int) -> None:
        page = self._page
        frame = page.frame_locator(cfg.FRAME_EDITOR)
        print(f"  editor step 1: {card_count} cards")
        frame.locator(cfg.SEL_STEP1_CARD_NUMBER).fill(str(card_count))
        # Proceeding uses the parent-level button, not the one in the iframe.
        page.locator(cfg.SEL_NEXT_STEP).click()
        page.wait_for_load_state("networkidle")

    # ---- fronts: upload + autofill (confirmed JS hooks) ------------------ #
    def _customize_fronts(self, fronts: list[Path]) -> None:
        page = self._page
        print(f"  fronts: uploading {len(fronts)} images, then autofill")
        page.evaluate(cfg.JS_OPEN_UPLOAD)   # oDesign.applyPopupPhoto()
        self._upload_files(fronts, what="front")
        page.evaluate(cfg.JS_AUTOFILL)      # oDesign.setAutoFill()
        self._pause("  Verify fronts autofilled correctly, then press Enter...")
        page.evaluate(cfg.JS_NEXT_STEP)
        page.wait_for_load_state("networkidle")

    # ---- backs ----------------------------------------------------------- #
    def _assign_backs(self, plan: UploadPlan) -> None:
        print(f"  backs: {len(plan.unique_backs)} image(s) "
              "(common Encounter/Player + unique quest backs)")
        self._upload_files(plan.unique_backs, what="back")
        self._pause("  Assign each back to its slot(s), then press Enter...")

    def _upload_files(self, files: list[Path], what: str) -> None:
        """Set the popup's file input to bulk-upload images.

        The photo popup renders async inside the canvas editor; its file-input
        selector must be confirmed during a local headed run. Until then, the
        operator drops the files and we continue.
        """
        page = self._page
        try:
            file_input = page.locator("input[type=file]").first
            file_input.set_input_files([str(f) for f in files], timeout=5000)
            print(f"    uploaded {len(files)} {what} image(s)")
        except Exception:
            print(f"    [confirm locally] upload these {len(files)} {what} images "
                  "in the popup:")
            self._pause("    Press Enter once uploaded...")

    def _go_to_cart(self) -> None:
        print(f"Navigating to cart: {cfg.CART_URL}")
        self._page.goto(cfg.CART_URL, wait_until="domcontentloaded")

    # ---- helpers --------------------------------------------------------- #
    @staticmethod
    def _pause(message: str) -> None:
        try:
            input(message)
        except EOFError:
            pass
