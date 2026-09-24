from datetime import timezone

from mysql.connector import Error as MySQLError

from app.db.connection import get_connection
from app.services.product_service import decimal_to_money, get_product_by_id
from app.utils.errors import database_error


def _format_timestamp(dt):
    if dt is None:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _fetch_price_and_offer_rows(product_id):
    conn = None
    try:
        conn = get_connection()
        cursor = conn.cursor(dictionary=True)

        cursor.execute(
            """
            SELECT pr.platform_id, pl.name AS platform, pr.price, pr.currency,
                   pr.available, pr.updated_at
            FROM prices pr
            JOIN platforms pl ON pl.id = pr.platform_id
            WHERE pr.product_id = %s
            """,
            (product_id,),
        )
        price_rows = cursor.fetchall()

        cursor.execute(
            """
            SELECT platform_id, title, description, discount_amount
            FROM offers
            WHERE product_id = %s AND is_active = TRUE
            """,
            (product_id,),
        )
        offer_rows = cursor.fetchall()
        cursor.close()
        return price_rows, offer_rows
    except MySQLError:
        raise database_error()
    finally:
        if conn is not None:
            conn.close()


def get_comparison(product_id):
    # Raises PRODUCT_NOT_FOUND / DATABASE_ERROR as needed.
    product = get_product_by_id(product_id)

    price_rows, offer_rows = _fetch_price_and_offer_rows(product_id)

    offers_by_platform = {
        row["platform_id"]: {
            "title": row["title"],
            "description": row["description"],
            "discount_amount": decimal_to_money(row["discount_amount"]),
        }
        for row in offer_rows
    }

    entries = []
    for row in price_rows:
        entries.append(
            {
                "platform_id": row["platform_id"],
                "platform": row["platform"],
                "price": decimal_to_money(row["price"]),
                "currency": row["currency"],
                "available": bool(row["available"]),
                "offer": offers_by_platform.get(row["platform_id"]),
                "updated_at": row["updated_at"],
            }
        )

    # Ordering rule (API_CONTRACT.md 3.5):
    #   1. Available platforms first, cheapest -> most expensive.
    #   2. Ties broken by platform_id ascending.
    #   3. Unavailable platforms last, ordered by platform_id.
    available_entries = [e for e in entries if e["available"]]
    unavailable_entries = [e for e in entries if not e["available"]]

    available_entries.sort(key=lambda e: (e["price"], e["platform_id"]))
    unavailable_entries.sort(key=lambda e: e["platform_id"])

    ordered = available_entries + unavailable_entries

    # Summary rule: only available prices count.
    if available_entries:
        lowest_price = available_entries[0]["price"]
        highest_price = max(e["price"] for e in available_entries)
        potential_saving = round(highest_price - lowest_price, 2)
        # available_entries is already sorted by (price, platform_id) asc,
        # so the first entry is automatically the tie-break winner.
        best_platform = available_entries[0]["platform"]
    else:
        lowest_price = None
        highest_price = None
        potential_saving = None
        best_platform = None

    timestamps = [e["updated_at"] for e in entries if e["updated_at"] is not None]
    last_updated = _format_timestamp(max(timestamps)) if timestamps else None

    prices_out = [
        {
            "platform_id": e["platform_id"],
            "platform": e["platform"],
            "price": e["price"],
            "currency": e["currency"],
            "available": e["available"],
            "offer": e["offer"],
        }
        for e in ordered
    ]

    return {
        "product": product,
        "prices": prices_out,
        "summary": {
            "lowest_price": lowest_price,
            "highest_price": highest_price,
            "potential_saving": potential_saving,
            "best_platform": best_platform,
        },
        "meta": {
            "data_source": "demo",
            "last_updated": last_updated,
        },
    }
