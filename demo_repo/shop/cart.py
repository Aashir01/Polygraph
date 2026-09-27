"""Cart — holds line items and computes a subtotal."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict


@dataclass
class LineItem:
    sku: str
    unit_price: float
    quantity: int


class Cart:
    """A shopping cart that tracks items by SKU."""

    def __init__(self) -> None:
        self._items: Dict[str, LineItem] = {}

    def add_item(self, sku: str, unit_price: float, quantity: int = 1) -> None:
        """Add *quantity* units of *sku* to the cart."""
        if sku in self._items:
            self._items[sku].quantity += quantity
        else:
            self._items[sku] = LineItem(sku=sku, unit_price=unit_price, quantity=quantity)

    def remove_item(self, sku: str, quantity: int = 1) -> None:
        """Remove *quantity* units of *sku*.  Raises KeyError if SKU not in cart."""
        if sku not in self._items:
            raise KeyError(f"SKU {sku!r} not found in cart")
        # BUG-01: quantity is decremented but the line is never removed when it
        # reaches zero.  A zero-quantity ghost line remains and contributes 0
        # to subtotal — but callers iterating items() will see a spurious entry.
        self._items[sku].quantity -= quantity
        # CORRECT code would be:
        #   if self._items[sku].quantity <= 0:
        #       del self._items[sku]

    def items(self) -> list[LineItem]:
        return list(self._items.values())

    def subtotal(self) -> float:
        """Sum of unit_price × quantity for all line items."""
        return sum(item.unit_price * item.quantity for item in self._items.values())
