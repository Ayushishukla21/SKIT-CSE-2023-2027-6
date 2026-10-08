"""
Historical price retrieval (read-only) for GET /api/products/<id>/history.

Reads the append-only `price_history` table written by
price_monitor_service. Nothing here modifies data.

Ordering (stable): recorded_at ASC, platform_id ASC, id ASC.
Unavailable observations are returned with price = null.
"""

from datetime import timezone

from mysql.connector import Error as MySQLError

from app.db.connection import get_connection
from app.services.product_service import decimal_to_money, get_product_by_id
from app.utils.errors import database_error


def _format_timestamp(dt):
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _fetch_rows(product_id, platform_id):
    conn = None
    try:
        conn = get_connection()
        cursor = conn.cursor(dictionary=True)
        sql = (
            "SELECT platform_id, price, currency, available, recorded_at "
            "FROM price_history WHERE product_id = %s"
        )
        params = [product_id]
        if platform_id is not None:
            sql += " AND platform_id = %s"
            params.append(platform_id)
        sql += " ORDER BY recorded_at ASC, platform_id ASC, id ASC"
        cursor.execute(sql, params)
        rows = cursor.fetchall()
        cursor.close()
        return rows
    except MySQLError:
        raise database_error()
    finally:
        if conn is not None:
            conn.close()


def get_history(product_id, platform_id=None):
    # Raises PRODUCT_NOT_FOUND / DATABASE_ERROR as needed.
    get_product_by_id(product_id)
    rows = _fetch_rows(product_id, platform_id)
    return {
        "product_id": product_id,
        "history": [
            {
                "platform_id": r["platform_id"],
                "price": decimal_to_money(r["price"]),
                "currency": r["currency"],
                "available": bool(r["available"]),
                "recorded_at": _format_timestamp(r["recorded_at"]),
            }
            for r in rows
        ],
    }
