"""Optional self-contained Playwright driver for MakePlayingCards.

This ports the proven upload/insert mechanism from chilli-axe/mpc-autofill's
``src/driver.py`` to Playwright, so LOTRAutofill can drive MPC without cloning
the desktop tool. The primary/recommended path remains `export` + `autofill`
(the desktop tool itself); this driver is a convenience alternative.

Flow (mirrors the desktop tool):
  1. product page: select cardstock + deck-size bracket
  2. doPersonalize() -> editor; in #sysifm_loginFrame set card count + "different
     images" mode
  3. fronts: for each unique image, upload to #uploadId then place it in each of
     its slots via PageLayout.prototype.applyDragPhoto(...)
  4. page to backs, repeat (or "same image" mode if a single common back)
  5. page to review -> stop (never orders)

Selectors/JS are from the live site; the operator signs in. Because it needs a
logged-in session and a live canvas editor, this driver should be validated on a
real headed run.
"""

from __future__ import annotations

import hashlib
import time
from pathlib import Path

from . import config as cfg
from .config import DEFAULT_PRODUCT, MpcProductConfig
from .plan import UploadPlan

_POLL_SECONDS = 0.5
_MAX_WAIT_SECONDS = 60


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

        front_slots = _slots_by_image(plan, face="front")
        back_slots = _slots_by_image(plan, face="back")

        self._launch()
        try:
            self._require_login()
            self._configure_product(tier)
            self._page_to_fronts(plan.total_cards)
            print(f"  fronts: {len(front_slots)} images")
            self._upload_and_insert(front_slots)
            self._page_to_backs(single_back=len(back_slots) == 1)
            print(f"  backs: {len(back_slots)} image(s)")
            self._upload_and_insert(back_slots, same_image=len(back_slots) == 1)
            self._page_to_review()

            print("\nProject filled. Review it and order manually — nothing was "
                  "purchased.")
            self._pause("Press Enter to close the browser...")
            return 0
        finally:
            self.close()

    # ---- login (operator types credentials) ------------------------------ #
    def _require_login(self) -> None:
        self._page.goto("https://www.makeplayingcards.com/login.aspx",
                        wait_until="domcontentloaded")
        print("Sign in to your MPC account in the opened window.")
        self._pause("Press Enter once you are signed in...")

    # ---- product configuration ------------------------------------------- #
    def _configure_product(self, deck_tier: int) -> None:
        page = self._page
        p = self.product
        print(f"Opening product page: {cfg.PRODUCT_URL}")
        page.goto(cfg.PRODUCT_URL, wait_until="domcontentloaded")
        self._reject_cookies()
        print(f"  card stock -> {p.card_stock}; deck size -> {deck_tier}")
        page.select_option(cfg.SEL_CARD_STOCK, value=p.card_stock_value)
        page.select_option(cfg.SEL_DECK_SIZE, value=str(deck_tier))

    def _reject_cookies(self) -> None:
        try:
            self._page.get_by_role("link", name="Reject").click(timeout=3000)
        except Exception:
            pass

    # ---- paging ---------------------------------------------------------- #
    def _page_to_fronts(self, card_count: int) -> None:
        page = self._page
        print("  entering editor...")
        page.evaluate(f"doPersonalize('{cfg.ACCEPT_SETTINGS_URL}');")
        page.wait_for_load_state("domcontentloaded")
        frame = self._editor_frame()
        if frame is not None:
            _try(lambda: frame.fill(cfg.SEL_STEP1_CARD_NUMBER, str(card_count)))
            _try(lambda: frame.evaluate(cfg.JS_SET_DIFFERENT_IMAGES))
        self._wait_spinner()

    def _page_to_backs(self, single_back: bool) -> None:
        self._next_step()
        try:
            close_btn = self._page.query_selector(cfg.SEL_CLOSE_BTN)
            if close_btn and close_btn.is_visible():
                close_btn.click()
        except Exception:
            pass
        self._next_step()
        frame = self._editor_frame()
        if frame is not None:
            js = cfg.JS_SET_SAME_IMAGE if single_back else cfg.JS_SET_DIFFERENT_IMAGES
            _try(lambda: frame.evaluate(js))
        self._wait_spinner()

    def _page_to_review(self) -> None:
        self._next_step()
        self._next_step()

    def _next_step(self) -> None:
        self._wait_spinner()
        _try(lambda: self._page.evaluate(cfg.JS_NEXT_STEP))
        self._wait_spinner()

    # ---- upload + insert (the core, ported from driver.py) --------------- #
    def _upload_and_insert(self, by_image: "dict[Path, list[int]]",
                           same_image: bool = False) -> None:
        page = self._page
        uploaded = set(self._uploaded_pids())
        for path, slots in by_image.items():
            pid = _pid(path)
            if pid not in uploaded:
                print(f"    uploading {path.name}")
                page.set_input_files(cfg.SEL_UPLOAD_INPUT, str(path))
                self._wait_upload()
                uploaded = set(self._uploaded_pids())
            if same_image:
                continue  # one image applied to the whole face by MPC
            for slot in sorted(slots):
                el = f'PageLayout.prototype.getElement3("dnImg","{slot}")'
                _try(lambda el=el, pid=pid: page.evaluate(
                    f'PageLayout.prototype.applyDragPhoto({el}, 0, "{pid}")'))
                self._wait_spinner()

    # ---- editor helpers -------------------------------------------------- #
    def _editor_frame(self):
        el = self._page.query_selector(cfg.FRAME_EDITOR)
        return el.content_frame() if el else None

    def _uploaded_pids(self) -> "list[str]":
        js = ("(typeof oDesignImage !== 'undefined' && oDesignImage.dn_getImageList)"
              " ? oDesignImage.dn_getImageList() : ''")
        result = _try(lambda: self._page.evaluate(js)) or ""
        return [p for p in result.split(";") if p]

    def _wait_upload(self) -> None:
        deadline = time.time() + _MAX_WAIT_SECONDS
        while time.time() < deadline:
            uploading = _try(lambda: self._page.evaluate(
                "typeof oDesignImage !== 'undefined' && "
                "oDesignImage.UploadStatus == 'Uploading'"))
            if not uploading:
                return
            time.sleep(_POLL_SECONDS)

    def _wait_spinner(self) -> None:
        try:
            self._page.wait_for_selector(cfg.SEL_WAIT_SPINNER, state="hidden",
                                         timeout=_MAX_WAIT_SECONDS * 1000)
        except Exception:
            pass

    @staticmethod
    def _pause(message: str) -> None:
        try:
            input(message)
        except EOFError:
            pass


# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #
def _slots_by_image(plan: UploadPlan, face: str) -> "dict[Path, list[int]]":
    """Map each image path to the 0-indexed slots it fills, in first-seen order."""
    out: "dict[Path, list[int]]" = {}
    for i, slot in enumerate(plan.slots):
        img = slot.front if face == "front" else slot.back
        if img is not None:
            out.setdefault(img, []).append(i)
    return out


def _pid(path: Path) -> str:
    return hashlib.sha1(Path(path).read_bytes()).hexdigest().upper()


def _try(fn):
    """Run a Playwright/JS call, swallowing transient JS errors (as the desktop
    tool does with @ignore_javascript_errors)."""
    try:
        return fn()
    except Exception:
        return None
