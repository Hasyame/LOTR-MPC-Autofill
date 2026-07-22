"""Tests for the MPC price estimate (tiers, stock/foil multipliers, currency)."""

from lotrautofill.mpc import pricing


def test_bills_up_to_the_next_deck_tier():
    # 20 cards is billed as MPC's 36-card deck tier.
    assert pricing._billed_cards(20) == 36
    assert pricing._billed_cards(18) == 18
    assert pricing._billed_cards(1) == 18


def test_large_order_splits_into_612_decks():
    # 700 = one full 612 deck + a 90-card tier for the remaining 88.
    assert pricing._billed_cards(700) == 612 + 90


def test_estimate_shape_and_currencies():
    e = pricing.estimate(55, "(S30) Standard Smooth", foil=False)
    assert e["cards"] == 55 and e["billed_cards"] == 55
    assert set(e["prices"]) == {"USD", "EUR", "CNY"}
    # Baseline stock, no foil: USD equals the raw tier price.
    assert e["prices"]["USD"] == round(pricing._DECK_PRICE_USD[55], 2)
    assert e["date"] == pricing.PRICE_DATE_DISPLAY


def test_over_612_flags_multiple_projects():
    over = pricing.estimate(700)
    assert over["over_max"] is True
    assert over["max_per_project"] == 612
    assert over["projects"] == 2                 # ceil(700 / 612)
    under = pricing.estimate(600)
    assert under["over_max"] is False and under["projects"] == 1
    assert pricing.estimate(612)["over_max"] is False   # exactly the cap is OK


def test_foil_and_stock_raise_the_price():
    base = pricing.estimate(55, "(S30) Standard Smooth", foil=False)["prices"]["USD"]
    foil = pricing.estimate(55, "(S30) Standard Smooth", foil=True)["prices"]["USD"]
    superior = pricing.estimate(55, "(S33) Superior Smooth", foil=False)["prices"]["USD"]
    assert foil > base and superior > base


def test_empty_cart_is_free():
    e = pricing.estimate(0)
    assert e["prices"] == {"USD": 0.0, "EUR": 0.0, "CNY": 0.0}
    assert e["billed_cards"] == 0
