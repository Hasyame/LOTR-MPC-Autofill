"""Tests for MPC deck-size tier selection."""

from lotrautofill.mpc.config import (
    DEFAULT_PRODUCT,
    MPC_MAX_CARDS_PER_PROJECT,
    deck_size_tier,
)


def test_exact_tier():
    assert deck_size_tier(55) == 55


def test_rounds_up_to_next_tier():
    assert deck_size_tier(204) == 216      # Khazad-dûm
    assert deck_size_tier(400) == 504      # Hobbit Saga
    assert deck_size_tier(1) == 18


def test_max_tier():
    assert deck_size_tier(612) == 612
    assert MPC_MAX_CARDS_PER_PROJECT == 612


def test_over_limit_raises():
    try:
        deck_size_tier(700)
    except ValueError:
        return
    raise AssertionError("expected ValueError for >612 cards")


def test_default_product_card_stock():
    assert DEFAULT_PRODUCT.card_stock_value == "PA_060"
