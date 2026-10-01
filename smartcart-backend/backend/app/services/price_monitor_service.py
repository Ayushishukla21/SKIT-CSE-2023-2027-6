"""
Price-monitoring data-update workflow.

Receives incoming price records (from a future scraper, a CSV, or an admin
call), validates and normalises them, then updates the CURRENT price in
`prices` and logs genuine changes in `price_history`.

Record shape (dict):
    product_id   int, required, must exist in products
    platform_id  int 1-4, required, must exist in platforms
    price        number/str, > 0 (e.g. 65, "65.00", "Rs 1,299.5"); ignored if unavailable
    available    bool / "true"/"false", default True
    currency     default "INR" (only INR supported)
    observed_at  ISO 8601 string or datetime, default = now (UTC)

Rules:
  * price is the FINAL selling price; offers are never subtracted here.
  * unavailable  ->  price NULL + available false.
  * Repeating the same data is safe: no duplicate history row. A newer
    observed_at on unchanged data only refreshes prices.updated_at
    (the price was re-confirmed then); an older observed_at is ignored as stale.
  * prices.updated_at is the observation time, never the time of a no-op call.
"""

import math
import re
from datetime import datetime, timezone
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation

from mysql.connector import Error as MySQLError

from app.db.connection import get_connection
from app.utils.errors import (
    ApiError,
    database_error,
    invalid_parameter,
    invalid_platform_id,
    invalid_price,
    invalid_product_id,
    product_not_found,
)

SUPPORTED_CURRENCY = "INR"
MAX_PRICE = Decimal("99999999.99")  # DECIMAL(10,2)

STATUS_INSERTED = "inserted"
STATUS_UPDATED = "updated"
STATUS_UNCHANGED = "unchanged"
STATUS_STALE = "stale"


# --- normalisation / validation ---------------------------------------

def _to_positive_int(value, error_factory):
    if isinstance(value, bool) or value is None:
        raise error_factory()
    if isinstance(value, int):
        number = value
    elif isinstance(value, float):
        if not value.is_integer():
            raise error_factory()
        number = int(value)
    else:
        text = str(value).strip()
        if not text.isdigit():
            raise error_factory()
        number = int(text)
    if number <= 0:
        raise error_factory()
    return number


def normalize_product_id(value):
    return _to_positive_int(value, invalid_product_id)


def normalize_platform_id(value):
    platform_id = _to_positive_int(value, invalid_platform_id)
    if not 1 <= platform_id <= 4:
        raise invalid_platform_id()
    return platform_id


def normalize_available(value):
    if value is None:
        return True
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)) and value in (0, 1):
        return bool(value)
    text = str(value).strip().lower()
    if text in ("true", "1", "yes"):
        return True
    if text in ("false", "0", "no"):
        return False
    raise invalid_parameter("available must be true or false")


def normalize_price(value):
    """Returns Decimal rounded to 2 dp, > 0. Accepts '₹1,299.5' style input."""
    if value is None or isinstance(value, bool):
        raise invalid_price()
    if isinstance(value, float):
        if not math.isfinite(value):
            raise invalid_price()
        text = repr(value)
    else:
        text = str(value).strip()
        text = re.sub(r"^(₹|rs\.?|inr)\s*", "", text, flags=re.IGNORECASE)
        text = text.replace(",", "").strip()
    try:
        price = Decimal(text)
    except (InvalidOperation, ValueError):
        raise invalid_price()
    if not price.is_finite():
        raise invalid_price()
    price = price.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    if price <= 0 or price > MAX_PRICE:
        raise invalid_price()
    return price


def normalize_currency(value):
    if value is None or str(value).strip() == "":
        return SUPPORTED_CURRENCY
    currency = str(value).strip().upper()
    if currency != SUPPORTED_CURRENCY:
        raise invalid_parameter("Only INR prices are supported")
    return currency


def normalize_observed_at(value, now=None):
    """Returns a naive UTC datetime (what the DATETIME column stores)."""
    if value is None or (isinstance(value, str) and value.strip() == ""):
        dt = now or datetime.now(timezone.utc)
    elif isinstance(value, datetime):
        dt = value
    else:
        text = str(value).strip()
        if text.endswith(("Z", "z")):
            text = text[:-1] + "+00:00"
        try:
            dt = datetime.fromisoformat(text)
        except ValueError:
            raise invalid_parameter("observed_at must be an ISO 8601 timestamp")
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    dt = dt.astimezone(timezone.utc)
    return dt.replace(tzinfo=None, microsecond=0)


def validate_record(record, now=None):
    """Validates + normalises one incoming record (no DB access)."""
    if not isinstance(record, dict):
        raise invalid_parameter("Price record must be an object")

    product_id = normalize_product_id(record.get("product_id"))
    platform_id = normalize_platform_id(record.get("platform_id"))
    available = normalize_available(record.get("available"))
    currency = normalize_currency(record.get("currency"))
    observed_at = normalize_observed_at(record.get("observed_at"), now)

    if available:
        price = normalize_price(record.get("price"))
    else:
        price = None  # unavailable => price NULL, whatever was sent

    return {
        "product_id": product_id,
        "platform_id": platform_id,
        "price": price,
        "currency": currency,
        "available": available,
        "observed_at": observed_at,
    }


# --- persistence -------------------------------------------------------

def _same_price(a, b):
    if a is None or b is None:
        return a is None and b is None
    return Decimal(str(a)).quantize(Decimal("0.01")) == Decimal(str(b)).quantize(Decimal("0.01"))


def _apply(conn, rec):
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("SELECT id FROM products WHERE id = %s", (rec["product_id"],))
        if cursor.fetchone() is None:
            raise product_not_found()
        cursor.execute("SELECT id FROM platforms WHERE id = %s", (rec["platform_id"],))
        if cursor.fetchone() is None:
            raise invalid_platform_id()

        cursor.execute(
            "SELECT price, currency, available, updated_at FROM prices "
            "WHERE product_id = %s AND platform_id = %s FOR UPDATE",
            (rec["product_id"], rec["platform_id"]),
        )
        current = cursor.fetchone()

        if current is None:
            cursor.execute(
                "INSERT INTO prices (product_id, platform_id, price, currency, available, updated_at) "
                "VALUES (%s, %s, %s, %s, %s, %s)",
                (rec["product_id"], rec["platform_id"], rec["price"], rec["currency"],
                 rec["available"], rec["observed_at"]),
            )
            status, log_history = STATUS_INSERTED, True
        else:
            stored_at = current["updated_at"]
            if isinstance(stored_at, str):
                stored_at = datetime.fromisoformat(stored_at)
            if stored_at is not None and rec["observed_at"] < stored_at:
                return STATUS_STALE
            unchanged = (
                _same_price(current["price"], rec["price"])
                and bool(current["available"]) == rec["available"]
                and current["currency"] == rec["currency"]
            )
            if unchanged:
                if stored_at is not None and rec["observed_at"] == stored_at:
                    return STATUS_UNCHANGED
                cursor.execute(
                    "UPDATE prices SET updated_at = %s WHERE product_id = %s AND platform_id = %s",
                    (rec["observed_at"], rec["product_id"], rec["platform_id"]),
                )
                return STATUS_UNCHANGED
            cursor.execute(
                "UPDATE prices SET price = %s, currency = %s, available = %s, updated_at = %s "
                "WHERE product_id = %s AND platform_id = %s",
                (rec["price"], rec["currency"], rec["available"], rec["observed_at"],
                 rec["product_id"], rec["platform_id"]),
            )
            status, log_history = STATUS_UPDATED, True

        if log_history:
            cursor.execute(
                "INSERT INTO price_history (product_id, platform_id, price, currency, available, recorded_at) "
                "VALUES (%s, %s, %s, %s, %s, %s)",
                (rec["product_id"], rec["platform_id"], rec["price"], rec["currency"],
                 rec["available"], rec["observed_at"]),
            )
        return status
    finally:
        cursor.close()


def update_price(record, conn_factory=get_connection, now=None):
    """
    Validates and applies ONE price record in its own transaction.

    Returns {"product_id", "platform_id", "status", "price", "available", "observed_at"}
    Raises ApiError for invalid input / unknown product / database problems.
    """
    rec = validate_record(record, now)
    conn = None
    try:
        conn = conn_factory()
        try:
            status = _apply(conn, rec)
            conn.commit()
        except Exception:
            conn.rollback()
            raise
    except ApiError:
        raise
    except MySQLError:
        raise database_error()
    finally:
        if conn is not None:
            try:
                conn.close()
            except MySQLError:
                pass

    return {
        "product_id": rec["product_id"],
        "platform_id": rec["platform_id"],
        "status": status,
        "price": float(rec["price"]) if rec["price"] is not None else None,
        "available": rec["available"],
        "observed_at": rec["observed_at"].strftime("%Y-%m-%dT%H:%M:%SZ"),
    }


def update_prices(records, conn_factory=get_connection, now=None):
    """
    Applies many records. A bad record is reported in `errors` and does not
    stop the others; a database failure aborts the batch (DATABASE_ERROR).
    """
    results, errors = [], []
    for index, record in enumerate(records):
        try:
            results.append(update_price(record, conn_factory, now))
        except ApiError as err:
            if err.code == "DATABASE_ERROR":
                raise
            errors.append({"index": index, "code": err.code, "message": err.message})
    return {"results": results, "errors": errors}
