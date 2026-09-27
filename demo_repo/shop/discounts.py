"""Discounts — tiered percentage discounts based on subtotal."""
from __future__ import annotations

# Tiered discount table: (minimum_subtotal, discount_rate)
# A subtotal that exactly equals a boundary earns that tier's discount.
TIERS: list[tuple[float, float]] = [
    (200.0, 0.20),
    (100.0, 0.10),
    (50.0,  0.05),
]


def apply_discount(subtotal: float, coupon_amount: float = 0.0) -> float:
    """
    Return the discounted price after applying the best tiered discount and
    then subtracting a flat coupon amount.

    Tiered discount rules:
      subtotal >= 200  →  20 % off
      subtotal >= 100  →  10 % off
      subtotal >=  50  →   5 % off
      subtotal  <  50  →   0 % off

    The coupon is applied after the percentage discount and cannot make the
    price negative.
    """
    rate = 0.0
    for threshold, tier_rate in TIERS:
        # BUG-02: strict '>' means a subtotal that equals the threshold exactly
        # misses the discount.  E.g. subtotal=100.0 → rate stays 0.0 instead
        # of 0.10.  The correct operator is '>='.
        if subtotal > threshold:
            rate = tier_rate
            break

    after_pct = subtotal * (1.0 - rate)
    return max(0.0, after_pct - coupon_amount)
