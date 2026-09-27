"""Tests for the shop.tax module."""
import pytest
from shop.tax import compute_tax


def test_tax_no_discount_no_coupon():
    # 8 % of 100 = 8.00
    assert compute_tax(100.00) == pytest.approx(8.00)


def test_tax_with_percentage_discount():
    # 10 % discount → taxable = 90, tax = 7.20
    assert compute_tax(100.00, discount_rate=0.10) == pytest.approx(7.20)


# BUG-03 regression: the coupon must be deducted BEFORE computing tax.
def test_tax_with_coupon():
    """Tax must be computed on subtotal minus discount minus coupon."""
    # subtotal=100, 10 % discount → 90, minus $10 coupon → taxable=80
    # tax = 80 * 0.08 = 6.40
    result = compute_tax(100.00, discount_rate=0.10, coupon_amount=10.00)
    assert result == pytest.approx(6.40), (
        "Tax should be computed on the post-coupon amount (80.00 * 0.08 = 6.40), "
        f"but got {result:.2f}.  Fix tax.py to deduct coupon_amount before taxing."
    )


def test_tax_large_coupon_clamps_to_zero():
    # Coupon bigger than discounted price → taxable clamped to 0 → tax = 0
    result = compute_tax(50.00, discount_rate=0.0, coupon_amount=60.00)
    assert result == pytest.approx(0.0)


def test_custom_tax_rate():
    assert compute_tax(200.00, tax_rate=0.05) == pytest.approx(10.00)
