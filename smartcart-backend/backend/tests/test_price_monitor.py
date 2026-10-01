"""
Tests for the price-monitoring update workflow.

These use an in-memory SQLite database behind a tiny MySQL-style adapter,
so they run without MySQL and never touch the real `smartcart` data.
"""

import sqlite3
from datetime import datetime, timezone
from decimal import Decimal

import pytest
from mysql.connector import Error as MySQLError

from app.services import price_monitor_service as svc
from app.utils.errors import ApiError

SCHEMA = """
CREATE TABLE platforms (id INTEGER PRIMARY KEY, name TEXT);
CREATE TABLE products (id INTEGER PRIMARY KEY, name TEXT);
CREATE TABLE prices (
    id INTEGER PRIMARY KEY AUTOINCREMENT, product_id INT, platform_id INT,
    price TEXT NULL, currency TEXT, available INT, updated_at TEXT,
    UNIQUE (product_id, platform_id));
CREATE TABLE price_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT, product_id INT, platform_id INT,
    price TEXT NULL, currency TEXT, available INT, recorded_at TEXT,
    UNIQUE (product_id, platform_id, recorded_at));
INSERT INTO platforms VALUES (1,'Blinkit'),(2,'Zepto'),(3,'Instamart'),(4,'Flipkart Minutes');
INSERT INTO products VALUES (1,'Amul Taaza Milk'),(2,'Aashirvaad Atta');
"""


class _Cursor:
    def __init__(self, raw, fail_on=None):
        self._c, self._fail_on = raw, fail_on

    def execute(self, sql, params=()):
        if self._fail_on and self._fail_on in sql:
            raise MySQLError("simulated failure")
        sql = sql.replace("%s", "?").replace(" FOR UPDATE", "")
        params = tuple(
            p.strftime("%Y-%m-%d %H:%M:%S") if isinstance(p, datetime)
            else str(p) if isinstance(p, Decimal) else p
            for p in params
        )
        self._c.execute(sql, params)

    def fetchone(self):
        row = self._c.fetchone()
        return dict(row) if row is not None else None

    def close(self):
        self._c.close()


class _Conn:
    def __init__(self, raw, fail_on=None):
        self._raw, self._fail_on = raw, fail_on

    def cursor(self, dictionary=False):
        return _Cursor(self._raw.cursor(), self._fail_on)

    def commit(self):
        self._raw.commit()

    def rollback(self):
        self._raw.rollback()

    def close(self):
        pass  # keep the in-memory DB alive across calls


@pytest.fixture()
def db():
    raw = sqlite3.connect(":memory:")
    raw.row_factory = sqlite3.Row
    raw.executescript(SCHEMA)
    return raw


def factory(db, fail_on=None):
    return lambda: _Conn(db, fail_on)


def price_row(db, product_id=1, platform_id=2):
    row = db.execute(
        "SELECT price, available, updated_at FROM prices WHERE product_id=? AND platform_id=?",
        (product_id, platform_id),
    ).fetchone()
    return dict(row) if row else None


def history_count(db):
    return db.execute("SELECT COUNT(*) FROM price_history").fetchone()[0]


def rec(**kw):
    base = {"product_id": 1, "platform_id": 2, "price": "65.00",
            "observed_at": "2026-10-01T10:00:00Z"}
    base.update(kw)
    return base


# --- valid update ----------------------------------------------------

def test_valid_price_inserts_price_and_history(db):
    result = svc.update_price(rec(), factory(db))
    assert result["status"] == "inserted"
    assert result["price"] == 65.0 and result["available"] is True
    row = price_row(db)
    assert Decimal(row["price"]) == Decimal("65.00") and row["available"] == 1
    assert history_count(db) == 1


def test_price_change_updates_latest_and_logs_history(db):
    svc.update_price(rec(), factory(db))
    result = svc.update_price(rec(price=62, observed_at="2026-10-01T11:00:00Z"), factory(db))
    assert result["status"] == "updated"
    assert Decimal(price_row(db)["price"]) == Decimal("62.00")
    assert history_count(db) == 2


def test_price_is_normalized(db):
    result = svc.update_price(rec(price=" ₹1,299.505 ", product_id="2"), factory(db))
    assert result["price"] == 1299.51
    assert result["product_id"] == 2


# --- invalid input ---------------------------------------------------

@pytest.mark.parametrize("bad", [0, -1, "abc", None, True, 1.5, ""])
def test_invalid_product_id(db, bad):
    with pytest.raises(ApiError) as exc:
        svc.update_price(rec(product_id=bad), factory(db))
    assert exc.value.code == "INVALID_PRODUCT_ID" and exc.value.status_code == 400


def test_unknown_product_id(db):
    with pytest.raises(ApiError) as exc:
        svc.update_price(rec(product_id=999), factory(db))
    assert exc.value.code == "PRODUCT_NOT_FOUND" and exc.value.status_code == 404
    assert price_row(db, 999) is None and history_count(db) == 0


@pytest.mark.parametrize("bad", [0, 5, -2, "x", None, 2.5, True])
def test_invalid_platform_id(db, bad):
    with pytest.raises(ApiError) as exc:
        svc.update_price(rec(platform_id=bad), factory(db))
    assert exc.value.code == "INVALID_PLATFORM_ID"
    assert history_count(db) == 0


@pytest.mark.parametrize("bad", [0, -5, "free", None, float("nan"), float("inf"), "-3", 10**9, True])
def test_invalid_price(db, bad):
    with pytest.raises(ApiError) as exc:
        svc.update_price(rec(price=bad), factory(db))
    assert exc.value.code == "INVALID_PRICE" and exc.value.status_code == 400
    assert price_row(db) is None


def test_invalid_currency_and_observed_at(db):
    with pytest.raises(ApiError) as exc:
        svc.update_price(rec(currency="USD"), factory(db))
    assert exc.value.code == "INVALID_PARAMETER"
    with pytest.raises(ApiError) as exc:
        svc.update_price(rec(observed_at="yesterday"), factory(db))
    assert exc.value.code == "INVALID_PARAMETER"


# --- unavailable -----------------------------------------------------

def test_unavailable_stores_null_price_even_if_price_sent(db):
    result = svc.update_price(rec(available=False, price="99"), factory(db))
    assert result["price"] is None and result["available"] is False
    row = price_row(db)
    assert row["price"] is None and row["available"] == 0


def test_unavailable_needs_no_price(db):
    svc.update_price(rec(available="false", price=None), factory(db))
    assert price_row(db)["price"] is None


def test_available_to_unavailable_and_back_is_logged(db):
    svc.update_price(rec(), factory(db))
    svc.update_price(rec(available=False, observed_at="2026-10-01T11:00:00Z"), factory(db))
    assert price_row(db)["available"] == 0
    svc.update_price(rec(observed_at="2026-10-01T12:00:00Z"), factory(db))
    assert price_row(db)["available"] == 1
    assert history_count(db) == 3


# --- timestamps ------------------------------------------------------

def test_observed_at_is_stored_as_utc(db):
    result = svc.update_price(rec(observed_at="2026-10-01T15:30:00+05:30"), factory(db))
    assert result["observed_at"] == "2026-10-01T10:00:00Z"
    assert price_row(db)["updated_at"] == "2026-10-01 10:00:00"


def test_naive_timestamp_treated_as_utc(db):
    svc.update_price(rec(observed_at="2026-10-01 10:00:00"), factory(db))
    assert price_row(db)["updated_at"] == "2026-10-01 10:00:00"


def test_missing_observed_at_defaults_to_now(db):
    fixed = datetime(2026, 10, 2, 8, 0, 0, tzinfo=timezone.utc)
    record = rec()
    del record["observed_at"]
    result = svc.update_price(record, factory(db), now=fixed)
    assert result["observed_at"] == "2026-10-02T08:00:00Z"


def test_older_observation_is_ignored_as_stale(db):
    svc.update_price(rec(price=65, observed_at="2026-10-01T12:00:00Z"), factory(db))
    result = svc.update_price(rec(price=50, observed_at="2026-10-01T09:00:00Z"), factory(db))
    assert result["status"] == "stale"
    row = price_row(db)
    assert Decimal(row["price"]) == Decimal("65.00")
    assert row["updated_at"] == "2026-10-01 12:00:00"
    assert history_count(db) == 1


# --- repeated updates ------------------------------------------------

def test_exact_repeat_is_idempotent(db):
    svc.update_price(rec(), factory(db))
    again = svc.update_price(rec(), factory(db))
    assert again["status"] == "unchanged"
    assert history_count(db) == 1
    assert db.execute("SELECT COUNT(*) FROM prices").fetchone()[0] == 1


def test_same_price_newer_time_only_refreshes_timestamp(db):
    svc.update_price(rec(), factory(db))
    again = svc.update_price(rec(observed_at="2026-10-01T18:00:00Z"), factory(db))
    assert again["status"] == "unchanged"
    assert price_row(db)["updated_at"] == "2026-10-01 18:00:00"
    assert history_count(db) == 1


# --- database failure ------------------------------------------------

def test_connection_failure_becomes_database_error():
    def broken():
        raise MySQLError("cannot connect: user=root password=secret")

    with pytest.raises(ApiError) as exc:
        svc.update_price(rec(), broken)
    assert exc.value.code == "DATABASE_ERROR" and exc.value.status_code == 503
    assert "secret" not in exc.value.message


def test_failure_mid_write_rolls_back_price(db):
    # prices row is written, then the history insert fails -> nothing persists
    with pytest.raises(ApiError) as exc:
        svc.update_price(rec(), factory(db, fail_on="INSERT INTO price_history"))
    assert exc.value.code == "DATABASE_ERROR"
    assert price_row(db) is None and history_count(db) == 0


# --- batch -----------------------------------------------------------

def test_batch_reports_bad_rows_and_continues(db):
    outcome = svc.update_prices(
        [rec(), rec(product_id=999), rec(platform_id=9), rec(platform_id=3, price="70")],
        factory(db),
    )
    assert [r["status"] for r in outcome["results"]] == ["inserted", "inserted"]
    assert [e["code"] for e in outcome["errors"]] == ["PRODUCT_NOT_FOUND", "INVALID_PLATFORM_ID"]
    assert [e["index"] for e in outcome["errors"]] == [1, 2]


def test_batch_aborts_on_database_error(db):
    def broken():
        raise MySQLError("down")

    with pytest.raises(ApiError) as exc:
        svc.update_prices([rec()], broken)
    assert exc.value.code == "DATABASE_ERROR"
