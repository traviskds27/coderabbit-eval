from decimal import Decimal

from orders import cents_to_money, money_to_cents


def test_cents_to_money():
    assert cents_to_money(1999) == Decimal("19.99")


def test_money_to_cents():
    assert money_to_cents(Decimal("19.99")) == 1999


def test_round_trip():
    for cents in (0, 1, 99, 100, 12345):
        assert money_to_cents(cents_to_money(cents)) == cents
