"""Rough MPC price estimate for poker-size (2.5" x 3.5") proxy orders.

⚠️ These are ESTIMATES, not quotes. MakePlayingCards' real prices change over
time and vary by promotion, region and shipping. When you re-check
makeplayingcards.com, update ``_DECK_PRICE_USD`` / ``STOCK_MULTIPLIER`` /
``FX`` and bump ``PRICE_DATE`` below. Shipping and taxes are NOT included.

MPC bills per "size of deck" tier (see ``config.DECK_SIZE_TIERS``): an order of
20 cards is billed as a 36-card deck. The estimate therefore rounds the card
count up to the next tier, and splits very large orders into 612-card decks.
"""

from __future__ import annotations

from .config import MPC_MAX_CARDS_PER_PROJECT, deck_size_tier

# When the tables below were last checked against makeplayingcards.com.
PRICE_DATE = "2026-07-21"          # ISO
PRICE_DATE_DISPLAY = "21/07/2026"  # DD/MM/YYYY, for the user-facing disclaimer

# Base price in USD per MPC deck-size tier, for the baseline stock
# (S30 Standard Smooth), MPC game-card finish, shrink-wrapped, no foil.
_DECK_PRICE_USD: dict[int, float] = {
    18: 6.90, 36: 11.50, 55: 15.50, 72: 19.00, 90: 22.50, 108: 26.00,
    126: 29.50, 144: 33.00, 162: 36.50, 180: 40.00, 198: 43.50, 216: 47.00,
    234: 50.50, 396: 82.00, 504: 103.00, 612: 123.00,
}

# Card-stock label -> price multiplier relative to the baseline stock.
STOCK_MULTIPLIER: dict[str, float] = {
    "(S30) Standard Smooth": 1.00,
    "(S33) Superior Smooth": 1.10,
    "(S27) Smooth": 0.95,
    "(M31) Linen": 1.08,
    "(P10) Plastic": 2.20,
}
FOIL_MULTIPLIER = 1.5

# USD -> currency (approximate, dated the same day as the prices above).
FX: dict[str, float] = {"USD": 1.0, "EUR": 0.92, "CNY": 7.25}
CURRENCY_SYMBOL: dict[str, str] = {"USD": "$", "EUR": "€", "CNY": "¥"}


def _billed_cards(total_cards: int) -> int:
    """Cards actually billed: round up to the next MPC deck tier, splitting
    orders larger than one deck into full 612-card decks + a remainder tier."""
    if total_cards <= 0:
        return 0
    billed, remaining = 0, total_cards
    while remaining > MPC_MAX_CARDS_PER_PROJECT:
        billed += MPC_MAX_CARDS_PER_PROJECT
        remaining -= MPC_MAX_CARDS_PER_PROJECT
    return billed + deck_size_tier(remaining)


def _base_usd(total_cards: int) -> float:
    """Baseline-stock USD for ``total_cards`` (decks of 612 + remainder tier)."""
    if total_cards <= 0:
        return 0.0
    usd, remaining = 0.0, total_cards
    while remaining > MPC_MAX_CARDS_PER_PROJECT:
        usd += _DECK_PRICE_USD[MPC_MAX_CARDS_PER_PROJECT]
        remaining -= MPC_MAX_CARDS_PER_PROJECT
    return usd + _DECK_PRICE_USD[deck_size_tier(remaining)]


def estimate(total_cards: int, stock: str = "(S33) Superior Smooth",
             foil: bool = False) -> dict:
    """Estimate the MPC price for ``total_cards`` at the given stock/finish.

    Returns a JSON-friendly dict: prices per currency, the per-card USD rate,
    how many cards are billed, and the estimate date for the disclaimer.
    """
    mult = STOCK_MULTIPLIER.get(stock, 1.0) * (FOIL_MULTIPLIER if foil else 1.0)
    usd = _base_usd(total_cards) * mult
    prices = {cur: round(usd * rate, 2) for cur, rate in FX.items()}
    per_card = round(usd / total_cards, 3) if total_cards else 0.0
    return {
        "cards": total_cards,
        "billed_cards": _billed_cards(total_cards),
        "stock": stock,
        "foil": foil,
        "prices": prices,
        "symbols": CURRENCY_SYMBOL,
        "per_card_usd": per_card,
        "date": PRICE_DATE_DISPLAY,
        "date_iso": PRICE_DATE,
    }
