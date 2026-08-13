"""Thin sqlite wrapper.

All queries must be parameterised — see README conventions.
"""

import sqlite3
from contextlib import contextmanager

DB_PATH = "orderly.db"


def connect():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


@contextmanager
def transaction():
    """Run a block inside a transaction, rolling back on failure."""
    conn = connect()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def query_one(sql, params=()):
    with transaction() as conn:
        row = conn.execute(sql, params).fetchone()
    return dict(row) if row else None


def query_all(sql, params=()):
    with transaction() as conn:
        rows = conn.execute(sql, params).fetchall()
    return [dict(r) for r in rows]
