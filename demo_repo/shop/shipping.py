"""Shipping — flat-rate shipping with a free-shipping threshold."""
from __future__ import annotations

FLAT_RATE = 5.99
FREE_SHIPPING_THRESHOLD = 75.0  # free when the customer pays >= $75


def compute_shipping(cart_subtotal: float) -> float:
    """
    Return the shipping charge.

    Shipping is free when the amount the customer actually pays is at or above
    FREE_SHIPPING_THRESHOLD; otherwise FLAT_RATE applies.

    NOTE – BUG-04 is here AND in order.py:
    This function receives cart_subtotal (pre-discount) instead of the actual
    amount paid (post-discount, post-coupon).  A heavily-discounted order
    whose final price is below the threshold is incorrectly given free
    shipping, or conversely an order whose post-discount total is above the
    threshold is incorrectly charged the flat rate.

    The parameter should be renamed `amount_paid` and Order.compute() must
    pass the correct value.
    """
    # BUG-04 (this file): the caller (Order.compute) passes cart.subtotal()
    # instead of the post-discount, post-coupon total.  The fix requires
    # changing Order.compute() to pass the correct value.
    if cart_subtotal >= FREE_SHIPPING_THRESHOLD:
        return 0.0
    return FLAT_RATE
