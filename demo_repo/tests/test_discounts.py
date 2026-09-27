"""Tests for the shop.discounts module."""
import pytest
from shop.discounts import apply_discount


def test_no_discount_below_50():
    assert apply_discount(49.99) == pytest.approx(49.99)


def test_five_percent_at_50():
    # subtotal == 50.00 → exactly the 5 % tier boundary → 5 % off
    assert apply_discount(50.00) == pytest.approx(47.50)


def test_five_percent_above_50():
    assert apply_discount(75.00) == pytest.approx(71.25)


# BUG-02 regression: a subtotal that exactly equals the 10 % tier boundary
# must receive the 10 % discount.  The CORRECT business rule is '>=' not '>'.
# DO NOT change this test to match the buggy source – the source must be fixed.
def test_ten_percent_at_exactly_100():
    """A $100.00 cart must receive exactly 10 % off → $90.00."""
    result = apply_discount(100.00)
    assert result == pytest.approx(90.00), (
        "subtotal=100.00 should trigger the 10 % tier (threshold is >= 100), "
        f"but got {result:.2f}.  Fix discounts.py: change '>' to '>='."
    )


def test_ten_percent_above_100():
    assert apply_discount(150.00) == pytest.approx(135.00)


def test_twenty_percent_at_exactly_200():
    # Boundary check for the 20 % tier
    assert apply_discount(200.00) == pytest.approx(160.00)


def test_twenty_percent_above_200():
    assert apply_discount(250.00) == pytest.approx(200.00)


def test_coupon_applied_after_percentage():
    # 10 % off 150 = 135, then -10 coupon = 125
    assert apply_discount(150.00, coupon_amount=10.00) == pytest.approx(125.00)


def test_coupon_cannot_make_price_negative():
    assert apply_discount(10.00, coupon_amount=50.00) == pytest.approx(0.0)
