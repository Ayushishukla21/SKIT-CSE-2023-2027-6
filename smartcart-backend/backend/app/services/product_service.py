from mysql.connector import Error as MySQLError

from app.db.connection import get_connection
from app.utils.errors import database_error, product_not_found


def decimal_to_quantity(value):
    """
    products.quantity -> API `quantity`.
    Contract example shows whole numbers without a decimal point
    ("quantity": 1), so we return an int when the value is whole and a
    float otherwise (e.g. a future 0.5 kg pack).
    """
    if value is None:
        return None
    as_float = float(value)
    return int(as_float) if as_float.is_integer() else as_float


def decimal_to_money(value):
    """
    prices.price / offers.discount_amount -> API number.
    Always a float rounded to 2 decimals, matching the contract's
    "max 2 decimals" rule (e.g. 65.0, 10.0).
    """
    if value is None:
        return None
    return round(float(value), 2)


def row_to_product(row):
    return {
        "id": row["id"],
        "name": row["name"],
        "brand": row["brand"],
        "category": row["category"],
        "quantity": decimal_to_quantity(row["quantity"]),
        "unit": row["unit"],
        "image_url": row["image_url"],
    }


def get_products(page, per_page, category=None):
    conn = None
    try:
        conn = get_connection()
        cursor = conn.cursor(dictionary=True)

        where_clause = ""
        params = []
        if category:
            where_clause = "WHERE category = %s"
            params.append(category)

        cursor.execute(f"SELECT COUNT(*) AS total FROM products {where_clause}", params)
        total = cursor.fetchone()["total"]

        offset = (page - 1) * per_page
        cursor.execute(
            f"""
            SELECT id, name, brand, category, quantity, unit, image_url
            FROM products
            {where_clause}
            ORDER BY id ASC
            LIMIT %s OFFSET %s
            """,
            params + [per_page, offset],
        )
        rows = cursor.fetchall()
        cursor.close()

        total_pages = (total + per_page - 1) // per_page if per_page else 0

        return {
            "products": [row_to_product(row) for row in rows],
            "pagination": {
                "page": page,
                "per_page": per_page,
                "total": total,
                "total_pages": total_pages,
            },
        }
    except MySQLError:
        raise database_error()
    finally:
        if conn is not None:
            conn.close()


def get_product_by_id(product_id):
    conn = None
    try:
        conn = get_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute(
            "SELECT id, name, brand, category, quantity, unit, image_url "
            "FROM products WHERE id = %s",
            (product_id,),
        )
        row = cursor.fetchone()
        cursor.close()
    except MySQLError:
        raise database_error()
    finally:
        if conn is not None:
            conn.close()

    if row is None:
        raise product_not_found()

    return row_to_product(row)
