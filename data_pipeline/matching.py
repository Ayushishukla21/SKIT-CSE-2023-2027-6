from data_pipeline.normalize import normalize_product


def products_match(product_a, product_b):
    """Return True when the normalized product details match."""
    normalized_a = normalize_product(product_a)
    normalized_b = normalize_product(product_b)

    fields = [
        "normalized_brand",
        "normalized_name",
        "normalized_quantity",
        "normalized_unit",
    ]

    return all(
        normalized_a[field] == normalized_b[field]
        for field in fields
    )