"""
Validation for path/query parameters, kept separate from routes so the
rules from API_CONTRACT.md are easy to find and test in one place.
"""

from app.utils.errors import empty_search_query, invalid_parameter, invalid_product_id


def validate_product_id(raw_id):
    """
    Validates the <id> path segment for /api/products/<id> and
    /api/products/<id>/compare.

    Contract rule (3.3): id must be a positive whole number. Anything else
    ("abc", "0", "-3", "1.5", "") raises INVALID_PRODUCT_ID - never a
    generic 404/400 from Flask.
    """
    if raw_id is None:
        raise invalid_product_id()

    text = str(raw_id).strip()

    # str.isdigit() rejects "", "-3", "1.5", "abc", " " - exactly what we want.
    if not text.isdigit():
        raise invalid_product_id()

    value = int(text)
    if value <= 0:
        raise invalid_product_id()

    return value


def validate_pagination(page_raw, per_page_raw):
    """
    Contract rule (3.2): page defaults to 1 (>= 1), per_page defaults to
    20 (1 to 50). Anything invalid raises INVALID_PARAMETER.
    """
    page = 1
    per_page = 20

    if page_raw is not None and str(page_raw).strip() != "":
        text = str(page_raw).strip()
        if not text.isdigit() or int(text) < 1:
            raise invalid_parameter("page must be a positive integer")
        page = int(text)

    if per_page_raw is not None and str(per_page_raw).strip() != "":
        text = str(per_page_raw).strip()
        if not text.isdigit() or not (1 <= int(text) <= 50):
            raise invalid_parameter("per_page must be an integer between 1 and 50")
        per_page = int(text)

    return page, per_page


def validate_search_query(q_raw, limit_raw):
    """
    Contract rule (3.4): q is required, trimmed, non-empty, max 100 chars.
    limit defaults to 20 (1 to 50).
    """
    if q_raw is None:
        raise empty_search_query()

    query = q_raw.strip()
    if query == "":
        raise empty_search_query()

    if len(query) > 100:
        raise invalid_parameter("Search query is too long")

    limit = 20
    if limit_raw is not None and str(limit_raw).strip() != "":
        text = str(limit_raw).strip()
        if not text.isdigit() or not (1 <= int(text) <= 50):
            raise invalid_parameter("limit must be an integer between 1 and 50")
        limit = int(text)

    return query, limit
