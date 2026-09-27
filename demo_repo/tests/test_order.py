"""Integration tests for the full Order pipeline."""
import pytest
from shop.cart import Cart
from shop.order import Order
from shop.shipping import FLAT_RATE, FREE_SHIPPING_THRESHOLD


def _cart(*items):
    """Helper: Cart.add_item(sku, price, qty) for each (sku, price, qty) tuple."""
    c = Cart()
    for sku, price, qty in items:
        c.add_item(sku, price, qty)
    return c


def test_order_no_discount():
    # subtotal = 40.00 (below every tier), no coupon
    # tax = 40 * 0.08 = 3.20, shipping = 5.99
    cart = _cart(("ITEM", 20.00, 2))
    summary = Order(cart).compute()
    assert summary.subtotal == pytest.approx(40.00)
    assert summary.after_discount == pytest.approx(40.00)
    assert summary.tax == pytest.approx(3.20)
    assert summary.shipping == pytest.approx(FLAT_RATE)
    assert summary.total == pytest.approx(40.00 + 3.20 + FLAT_RATE)


def test_order_with_tiered_discount():
    # subtotal = 150.00, 10 % off → 135.00, tax = 10.80, subtotal≥75 free ship
    cart = _cart(("WIDGET", 75.00, 2))
    summary = Order(cart).compute()
    assert summary.subtotal == pytest.approx(150.00)
    assert summary.discount_rate == pytest.approx(0.10)
    assert summary.after_discount == pytest.approx(135.00)
    assert summary.shipping == pytest.approx(0.0)


# BUG-04 regression: shipping must be decided on the amount the customer PAYS
# (post-discount + post-coupon), not on the raw cart subtotal.
def test_order_shipping_based_on_amount_paid_not_subtotal():
    """
    A cart with subtotal >= FREE_SHIPPING_THRESHOLD whose after-discount+coupon
    total falls below the threshold must be charged shipping.

    Scenario:
      subtotal = 160.00  (> 100 → 10 % off → after_pct = 144.00)
      $70 coupon → after_discount = 74.00
      74.00 < 75.00  → shipping must be FLAT_RATE

    The subtotal (160) is well above the free-shipping threshold (75), so if
    shipping is incorrectly checked against the subtotal the test will wrongly
    report free shipping.

    Fix: Order.compute() must pass `after_discount` to compute_shipping(), and
    compute_shipping() parameter must represent the amount the customer pays.
    """
    cart = _cart(("ITEM", 160.00, 1))   # subtotal = 160.00, tier = 10 %
    # 10 % off → 144.00, minus $70 coupon → 74.00 (just below free-ship threshold)
    summary = Order(cart, coupon_amount=70.00).compute()
    assert summary.after_discount == pytest.approx(74.00)
    assert summary.shipping == pytest.approx(FLAT_RATE), (
        f"Shipping should be {FLAT_RATE} because the customer pays 74.00 < "
        f"{FREE_SHIPPING_THRESHOLD}, but got {summary.shipping:.2f}.  "
        "Fix Order.compute() to pass after_discount to compute_shipping()."
    )


def test_order_total_is_sum_of_components():
    cart = _cart(("A", 30.00, 1), ("B", 20.00, 1))   # subtotal=50, 5% off
    summary = Order(cart).compute()
    assert summary.total == pytest.approx(
        summary.after_discount + summary.tax + summary.shipping
    )
