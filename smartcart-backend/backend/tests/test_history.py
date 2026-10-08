"""
Tests for GET /api/products/<id>/history and the update -> history workflow.

Runs against the real MySQL database (like test_compare.py) but only touches a
temporary product (id 9001) that is created and deleted per test; the cascade
removes its prices/history. Seeded demo data is never modified.
"""

import pytest

from app.db.connection import get_connection
from app.services import price_monitor_service as svc

PID = 9001


@pytest.fixture()
def hp(client):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM products WHERE id = %s", (PID,))
    cur.execute(
        "INSERT INTO products (id, name, brand, category, quantity, unit) "
        "VALUES (%s, 'History Test Item', 'Test', 'Test', 1, 'kg')", (PID,))
    conn.commit()
    yield PID
    cur.execute("DELETE FROM products WHERE id = %s", (PID,))
    conn.commit()
    cur.close()
    conn.close()


def rec(**kw):
    base = {"product_id": PID, "platform_id": 1, "price": 68,
            "observed_at": "2026-10-01T10:00:00Z"}
    base.update(kw)
    return base


def history(client, **params):
    r = client.get(f"/api/products/{PID}/history", query_string=params)
    return r, r.get_json()


def count_history(platform_id=None):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM price_history WHERE product_id=%s", (PID,))
    n = cur.fetchone()[0]
    cur.close()
    conn.close()
    return n


def current(platform_id=1):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT price FROM prices WHERE product_id=%s AND platform_id=%s",
                (PID, platform_id))
    row = cur.fetchone()
    cur.close()
    conn.close()
    return float(row[0])


# --- endpoint -----------------------------------------------------------

def test_history_valid_request_shape(client, hp):
    svc.update_price(rec())
    r, data = history(client)
    assert r.status_code == 200
    assert data == {
        "product_id": PID,
        "history": [{"platform_id": 1, "price": 68.0, "currency": "INR",
                     "available": True, "recorded_at": "2026-10-01T10:00:00Z"}],
    }


def test_history_unknown_product(client, hp):
    r = client.get("/api/products/999999/history")
    assert r.status_code == 404
    assert r.get_json() == {"error": {"code": "PRODUCT_NOT_FOUND", "message": "Product not found"}}


def test_history_invalid_product_id(client):
    r = client.get("/api/products/abc/history")
    assert r.status_code == 400
    assert r.get_json()["error"]["code"] == "INVALID_PRODUCT_ID"


def test_history_invalid_platform_filter(client, hp):
    r, data = history(client, platform_id=9)
    assert r.status_code == 400
    assert data["error"]["code"] == "INVALID_PLATFORM_ID"


def test_history_empty(client, hp):
    r, data = history(client)
    assert r.status_code == 200
    assert data == {"product_id": PID, "history": []}


def test_history_multiple_platforms_and_filter(client, hp):
    svc.update_price(rec(platform_id=1, price=68))
    svc.update_price(rec(platform_id=2, price=70))
    svc.update_price(rec(platform_id=3, price=66))
    _, data = history(client)
    assert [h["platform_id"] for h in data["history"]] == [1, 2, 3]
    _, filtered = history(client, platform_id=2)
    assert [(h["platform_id"], h["price"]) for h in filtered["history"]] == [(2, 70.0)]


def test_history_ordering_oldest_first_then_platform(client, hp):
    svc.update_price(rec(platform_id=2, price=70, observed_at="2026-10-02T10:00:00Z"))
    svc.update_price(rec(platform_id=1, price=68, observed_at="2026-10-02T10:00:00Z"))
    svc.update_price(rec(platform_id=1, price=60, observed_at="2026-10-03T10:00:00Z"))
    _, data = history(client)
    got = [(h["recorded_at"], h["platform_id"]) for h in data["history"]]
    assert got == [("2026-10-02T10:00:00Z", 1), ("2026-10-02T10:00:00Z", 2),
                   ("2026-10-03T10:00:00Z", 1)]


def test_history_unavailable_has_null_price(client, hp):
    svc.update_price(rec())
    svc.update_price(rec(available=False, price=None, observed_at="2026-10-02T10:00:00Z"))
    _, data = history(client)
    last = data["history"][-1]
    assert last["price"] is None and last["available"] is False
    assert data["history"][0]["price"] == 68.0  # old observation preserved


# --- update -> history workflow ----------------------------------------

def test_update_creates_history_and_current_price(client, hp):
    assert svc.update_price(rec())["status"] == "inserted"
    assert count_history() == 1 and current() == 68.0


def test_repeated_identical_update_no_duplicate_history(client, hp):
    svc.update_price(rec())
    assert svc.update_price(rec())["status"] == "unchanged"
    assert count_history() == 1


def test_stale_update_changes_nothing(client, hp):
    svc.update_price(rec(observed_at="2026-10-05T10:00:00Z", price=68))
    r = svc.update_price(rec(observed_at="2026-10-01T10:00:00Z", price=10))
    assert r["status"] == "stale"
    assert count_history() == 1 and current() == 68.0


def test_changed_price_creates_new_history_entry(client, hp):
    svc.update_price(rec())
    assert svc.update_price(rec(price=62, observed_at="2026-10-02T10:00:00Z"))["status"] == "updated"
    assert count_history() == 2 and current() == 62.0
    _, data = history(client)
    assert [h["price"] for h in data["history"]] == [68.0, 62.0]


def test_same_platform_different_times_are_not_duplicates(client, hp):
    svc.update_price(rec(price=68, observed_at="2026-10-01T10:00:00Z"))
    svc.update_price(rec(price=70, observed_at="2026-10-02T10:00:00Z"))
    svc.update_price(rec(price=68, observed_at="2026-10-03T10:00:00Z"))
    _, data = history(client, platform_id=1)
    assert [h["price"] for h in data["history"]] == [68.0, 70.0, 68.0]
