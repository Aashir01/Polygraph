"""Tax — compute sales tax on the taxable amount."""
from __future__ import annotations

DEFAULT_TAX_RATE = 0.08  # 8 %


def compute_tax(
    subtotal: float,
    discount_rate: float = 0.0,
    coupon_amount: float = 0.0,
    tax_rate: float = DEFAULT_TAX_RATE,
) -> float:
    """
    Return the tax owed.

    Tax is levied on the amount the customer actually pays:
        taxable = subtotal * (1 - discount_rate) - coupon_amount

    Both the percentage discount AND the coupon must be deducted before
    applying the tax rate.
    """
    # BUG-03: tax is computed on the post-percentage-discount price but the
    # coupon deduction is omitted, so coupon holders are overtaxed.
    # Correct formula:  taxable = subtotal * (1 - discount_rate) - coupon_amount
    after_discount = subtotal * (1.0 - discount_rate)
    # Missing:  after_discount -= coupon_amount
    taxable = max(0.0, after_discount)
    return round(taxable * tax_rate, 2)
