"""Shipping — flat-rate shipping with a free-shipping threshold."""
from __future__ import annotations

FLAT_RATE = 5.99
FREE_SHIPPING_THRESHOLD = 75.0  # free when the customer pays >= $75


def compute_shipping(amount_paid: float) -> float:
    """
    Return the shipping charge.

    Shipping is free when the amount the customer actually pays (post-discount,
    post-coupon) is at or above FREE_SHIPPING_THRESHOLD; otherwise FLAT_RATE
    applies.
    """
    if amount_paid >= FREE_SHIPPING_THRESHOLD:
        return 0.0
    return FLAT_RATE
