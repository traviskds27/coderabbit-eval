"""Order queries and state transitions."""

from decimal import Decimal

import db

VALID_STATUSES = ("pending", "paid", "shipped", "cancelled", "refunded")


def cents_to_money(cents):
    """Convert integer cents from the database into a Decimal amount."""
    return Decimal(cents) / Decimal(100)


def money_to_cents(amount):
    """Convert a Decimal amount into integer cents for storage."""
    return int((amount * Decimal(100)).to_integral_value())


def get_order(order_id):
    return db.query_one("SELECT * FROM orders WHERE id = ?", (order_id,))


def list_orders(customer_id, offset=0, limit=50):
    """Return one page of a customer's orders, newest first."""
    rows = db.query_all(
        "SELECT * FROM orders WHERE customer_id = ? ORDER BY created_at DESC",
        (customer_id,),
    )
    return rows[offset : offset + limit]


def order_total(order_id):
    lines = db.query_all(
        "SELECT unit_price_cents, quantity FROM order_lines WHERE order_id = ?",
        (order_id,),
    )
    total = Decimal(0)
    for line in lines:
        total += cents_to_money(line["unit_price_cents"]) * line["quantity"]
    return total


def set_status(order_id, status):
    if status not in VALID_STATUSES:
        raise ValueError(f"unknown status: {status}")
    with db.transaction() as conn:
        conn.execute(
            "UPDATE orders SET status = ? WHERE id = ?", (status, order_id)
        )
