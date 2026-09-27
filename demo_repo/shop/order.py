"""Order — assembles the full order total from all components."""
from __future__ import annotations
from dataclasses import dataclass

from .cart import Cart
from .discounts import TIERS, apply_discount
from .tax import compute_tax, DEFAULT_TAX_RATE
from .shipping import compute_shipping


def _discount_rate_for(subtotal: float) -> float:
    """Return the tiered discount rate that applies to *subtotal*."""
    for threshold, rate in TIERS:
        if subtotal >= threshold:
            return rate
    return 0.0


@dataclass
class OrderSummary:
    subtotal: float
    discount_rate: float
    discount_amount: float
    coupon_amount: float
    after_discount: float
    tax: float
    shipping: float
    total: float


class Order:
    """Computes the full cost breakdown for a cart."""

    def __init__(
        self,
        cart: Cart,
        coupon_amount: float = 0.0,
        tax_rate: float = DEFAULT_TAX_RATE,
    ) -> None:
        self.cart = cart
        self.coupon_amount = coupon_amount
        self.tax_rate = tax_rate

    def compute(self) -> OrderSummary:
        subtotal = self.cart.subtotal()
        discount_rate = _discount_rate_for(subtotal)
        after_discount = apply_discount(subtotal, self.coupon_amount)
        tax = compute_tax(
            subtotal,
            discount_rate=discount_rate,
            coupon_amount=self.coupon_amount,
            tax_rate=self.tax_rate,
        )
        shipping = compute_shipping(after_discount)
        total = after_discount + tax + shipping
        return OrderSummary(
            subtotal=subtotal,
            discount_rate=discount_rate,
            discount_amount=subtotal * discount_rate,
            coupon_amount=self.coupon_amount,
            after_discount=after_discount,
            tax=tax,
            shipping=shipping,
            total=total,
        )
