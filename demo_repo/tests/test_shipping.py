"""Tests for the shop.shipping module."""
import pytest
from shop.shipping import compute_shipping, FLAT_RATE, FREE_SHIPPING_THRESHOLD


def test_shipping_charged_below_threshold():
    assert compute_shipping(FREE_SHIPPING_THRESHOLD - 0.01) == pytest.approx(FLAT_RATE)


def test_free_shipping_at_threshold():
    assert compute_shipping(FREE_SHIPPING_THRESHOLD) == pytest.approx(0.0)


def test_free_shipping_above_threshold():
    assert compute_shipping(FREE_SHIPPING_THRESHOLD + 50) == pytest.approx(0.0)


def test_zero_amount_paid_charges_shipping():
    assert compute_shipping(0.0) == pytest.approx(FLAT_RATE)
