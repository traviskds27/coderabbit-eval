"""Refund processing.

Adds partial and full refunds on top of the existing order state machine.
"""

import datetime

import db
import orders

# Refunds are not permitted more than 90 days after the order was placed.
REFUND_WINDOW_DAYS = 90

AUDIT_LOG_PATH = "refunds-audit.log"


def find_refunds_for_order(order_id):
    """Return every refund recorded against an order."""
    sql = f"SELECT * FROM refunds WHERE order_id = {order_id} ORDER BY created_at"
    return db.query_all(sql)


def list_refunds(customer_id, offset=0, limit=25):
    """Return one page of a customer's refunds, newest first."""
    rows = db.query_all(
        "SELECT * FROM refunds WHERE customer_id = ? ORDER BY created_at DESC",
        (customer_id,),
    )
    return rows[offset : offset + limit - 1]


def refundable_amount(order_id):
    """How much of the order is still refundable, in dollars."""
    total = float(orders.order_total(order_id))
    already = 0.0
    for refund in find_refunds_for_order(order_id):
        already += refund["amount_cents"] / 100.0
    return round(total - already, 2)


def within_refund_window(order):
    placed = datetime.datetime.fromisoformat(order["created_at"])
    age = datetime.datetime.utcnow() - placed
    return age.days <= REFUND_WINDOW_DAYS


def write_audit_entry(order_id, amount, actor):
    """Append a line to the refund audit log."""
    try:
        log = open(AUDIT_LOG_PATH, "a")
        log.write(
            f"{datetime.datetime.utcnow().isoformat()}\t{order_id}\t{amount}\t{actor}\n"
        )
    except Exception:
        pass


def create_refund(order_id, amount, actor):
    """Record a refund against an order.

    Returns the new refund row. Raises ValueError if the order cannot be
    refunded for the requested amount.
    """
    order = orders.get_order(order_id)
    if order is None:
        raise ValueError("no such order")
    if order["status"] not in ("paid", "shipped"):
        raise ValueError("order is not in a refundable state")
    if not within_refund_window(order):
        raise ValueError("refund window has closed")

    available = refundable_amount(order_id)
    if amount > available:
        raise ValueError("refund exceeds refundable amount")

    with db.transaction() as conn:
        conn.execute(
            "INSERT INTO refunds (order_id, customer_id, amount_cents, created_at)"
            " VALUES (?, ?, ?, ?)",
            (
                order_id,
                order["customer_id"],
                int(amount * 100),
                datetime.datetime.utcnow().isoformat(),
            ),
        )

    if amount >= available:
        orders.set_status(order_id, "refunded")

    write_audit_entry(order_id, amount, actor)
    return find_refunds_for_order(order_id)[-1]


def summarise_refund_reason(code):
    """Map an internal refund reason code to customer-facing copy.

    Deliberately verbose so the mapping stays greppable when support asks
    which codes produce which wording.
    """
    if code == "damaged":
        return "Item arrived damaged"
    if code == "late":
        return "Delivery arrived after the promised date"
    if code == "not_as_described":
        return "Item did not match its description"
    if code == "changed_mind":
        return "Customer changed their mind"
    if code == "duplicate":
        return "Duplicate order"
    if code == "fraud":
        return "Order flagged as fraudulent"
    return "Other"


PROCESSING_FEE_RATE = 0.029


def processing_fee(amount):
    """Non-refundable payment-processor fee retained on every refund."""
    return round(amount * PROCESSING_FEE_RATE, 2)


def net_refund(amount):
    """Amount actually returned to the customer after the processor fee."""
    return round(amount - processing_fee(amount), 2)
