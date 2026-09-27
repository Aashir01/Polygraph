# demo_repo — shop package

A minimal Python e-commerce library used as a Polygraph test fixture.

## Structure

```
shop/           # library package
  cart.py       # Cart with add/remove and subtotal
  discounts.py  # tiered percentage discounts + coupon
  tax.py        # sales tax on net amount paid
  shipping.py   # flat-rate shipping with free-shipping threshold
  order.py      # assembles full order summary
tests/          # pytest suite (28 tests, 4 intentional failures)
tickets/        # Jira-style bug tickets for the 4 planted bugs
```

## Running the tests

```bash
# from the repo root
python -m pytest demo_repo/tests/ -v

# or from demo_repo/
cd demo_repo && python -m pytest tests/ -v
```

## Known bugs (baseline state)

| Ticket | File | Description |
|---|---|---|
| [SHOP-01](tickets/01.md) | `shop/cart.py` | Ghost line item with qty=0 after full removal |
| [SHOP-02](tickets/02.md) | `shop/discounts.py` | Tier boundary uses `>` instead of `>=` |
| [SHOP-03](tickets/03.md) | `shop/tax.py` | Coupon not deducted before computing tax |
| [SHOP-04](tickets/04.md) | `shop/order.py` + `shop/shipping.py` | Shipping checked against pre-discount subtotal |

> **Note on SHOP-02:** the tests encode the correct business rule.  Do not "fix"
> the tests — fix the source code.
