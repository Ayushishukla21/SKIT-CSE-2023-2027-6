import re


def normalize_text(value):
    """Standardize text for product matching without changing the original."""
    if value is None:
        return ""

    text = str(value).strip().lower()
    text = re.sub(r"\s+", " ", text)

    return text


def normalize_product(product):
    """Create normalized fields for matching while preserving original values."""
    return {
        "normalized_name": normalize_text(product.get("name")),
        "normalized_brand": normalize_text(product.get("brand")),
        "normalized_quantity": normalize_text(product.get("quantity")),
        "normalized_unit": normalize_text(product.get("unit")),
    }