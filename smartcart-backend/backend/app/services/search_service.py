from mysql.connector import Error as MySQLError

from app.db.connection import get_connection
from app.services.product_service import row_to_product
from app.utils.errors import database_error


def search_products(query, limit):
    """
    Case-insensitive search over name/brand/category (API_CONTRACT.md 3.4).
    Prefix matches on the product name are ranked first, then alphabetical -
    a simple, predictable "best matches first" ordering for a demo dataset.
    Empty-query / too-long validation happens in validators.py before this
    is called; an empty result set is a normal 200 response, not an error.
    """
    conn = None
    try:
        conn = get_connection()
        cursor = conn.cursor(dictionary=True)

        needle = query.lower()
        like_pattern = f"%{needle}%"
        prefix_pattern = f"{needle}%"

        cursor.execute(
            """
            SELECT id, name, brand, category, quantity, unit, image_url
            FROM products
            WHERE LOWER(name) LIKE %s OR LOWER(brand) LIKE %s OR LOWER(category) LIKE %s
            ORDER BY
                CASE WHEN LOWER(name) LIKE %s THEN 0 ELSE 1 END,
                name ASC
            LIMIT %s
            """,
            (like_pattern, like_pattern, like_pattern, prefix_pattern, limit),
        )
        rows = cursor.fetchall()
        cursor.close()
    except MySQLError:
        raise database_error()
    finally:
        if conn is not None:
            conn.close()

    products = [row_to_product(row) for row in rows]
    return {
        "query": query,
        "products": products,
        "count": len(products),
    }
