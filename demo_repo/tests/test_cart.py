"""Tests for the shop.cart module."""
import pytest
from shop.cart import Cart


def test_add_single_item():
    cart = Cart()
    cart.add_item("APPLE", 1.50, 3)
    assert len(cart.items()) == 1
    assert cart.subtotal() == pytest.approx(4.50)


def test_add_multiple_skus():
    cart = Cart()
    cart.add_item("APPLE", 1.50, 2)
    cart.add_item("BANANA", 0.80, 5)
    assert cart.subtotal() == pytest.approx(1.50 * 2 + 0.80 * 5)


def test_add_same_sku_twice_accumulates():
    cart = Cart()
    cart.add_item("APPLE", 1.50, 2)
    cart.add_item("APPLE", 1.50, 3)
    assert cart.items()[0].quantity == 5


def test_remove_item_partial():
    cart = Cart()
    cart.add_item("APPLE", 1.50, 5)
    cart.remove_item("APPLE", 2)
    assert cart.items()[0].quantity == 3
    assert cart.subtotal() == pytest.approx(4.50)


def test_remove_item_unknown_sku_raises():
    cart = Cart()
    cart.add_item("APPLE", 1.50)
    with pytest.raises(KeyError):
        cart.remove_item("BANANA")


# BUG-01 regression: removing all units of a SKU must eliminate the line item.
def test_remove_item_all_units_removes_line():
    """Removing every unit of a SKU must leave the cart empty."""
    cart = Cart()
    cart.add_item("APPLE", 1.50, 2)
    cart.remove_item("APPLE", 2)
    # After full removal the cart must have no items and a zero subtotal.
    assert cart.items() == [], "Ghost line item with qty=0 found after full removal"
    assert cart.subtotal() == pytest.approx(0.0)
