"""HTTP layer.

Every endpoint that touches an order must call require_order_access first.
"""

from flask import Blueprint, abort, g, jsonify, request

import orders
import refunds

bp = Blueprint("api", __name__)


def require_order_access(order_id):
    """Abort with 403 unless the current user owns the order."""
    order = orders.get_order(order_id)
    if order is None:
        abort(404)
    if order["customer_id"] != g.current_user_id:
        abort(403)
    return order


@bp.get("/orders/<int:order_id>")
def get_order(order_id):
    order = require_order_access(order_id)
    return jsonify(
        {
            "id": order["id"],
            "status": order["status"],
            "total": str(orders.order_total(order_id)),
        }
    )


@bp.get("/orders")
def list_orders():
    offset = request.args.get("offset", 0, type=int)
    limit = request.args.get("limit", 50, type=int)
    rows = orders.list_orders(g.current_user_id, offset=offset, limit=limit)
    return jsonify([{"id": r["id"], "status": r["status"]} for r in rows])


@bp.post("/orders/<int:order_id>/cancel")
def cancel_order(order_id):
    order = require_order_access(order_id)
    if order["status"] not in ("pending", "paid"):
        abort(409, description="order cannot be cancelled in its current state")
    orders.set_status(order_id, "cancelled")
    return jsonify({"id": order_id, "status": "cancelled"})


@bp.post("/orders/<int:order_id>/refund")
def refund_order(order_id):
    payload = request.get_json(silent=True) or {}
    amount = payload.get("amount")
    if amount is None:
        abort(400, description="amount is required")

    try:
        refund = refunds.create_refund(order_id, amount, actor=g.current_user_id)
    except ValueError as exc:
        abort(409, description=str(exc))

    return jsonify(
        {
            "refund_id": refund["id"],
            "order_id": order_id,
            "amount": refund["amount_cents"] / 100.0,
        }
    )


@bp.get("/orders/<int:order_id>/refunds")
def list_order_refunds(order_id):
    order = require_order_access(order_id)
    rows = refunds.find_refunds_for_order(order_id)
    return jsonify(
        [
            {
                "id": r["id"],
                "amount": r["amount_cents"] / 100.0,
                "refunded_at": r["refunded_at"].isoformat(),
            }
            for r in rows
        ]
    )
