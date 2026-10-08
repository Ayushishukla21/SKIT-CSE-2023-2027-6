from data_pipeline.price_processing import (
    normalize_price,
    normalize_platform,
    normalize_availability,
    validate_price_record,
)


VALID_PRODUCT_IDS = {1, 2, 3, 4, 5, 6}


def make_record(**overrides):
    record = {
        "product_id": "1",
        "platform": "Blinkit",
        "product_name": "Amul Taaza Milk",
        "price": "68.00",
        "available": "true",
        "quantity": "500",
        "unit": "ml",
        "timestamp": "2026-10-01T10:00:00Z",
    }

    record.update(overrides)
    return record


def test_valid_record_passes():
    assert validate_price_record(
        make_record(),
        VALID_PRODUCT_IDS,
    ) is None


def test_invalid_product_id_rejected():
    assert validate_price_record(
        make_record(product_id="999"),
        VALID_PRODUCT_IDS,
    ) == "Invalid product_id"


def test_invalid_platform_rejected():
    assert validate_price_record(
        make_record(platform="Unknown Platform"),
        VALID_PRODUCT_IDS,
    ) == "Invalid platform"


def test_negative_price_rejected():
    assert normalize_price("-20") is None


def test_nonnumeric_price_rejected():
    assert normalize_price("abc") is None


def test_invalid_availability_rejected():
    assert validate_price_record(
        make_record(available="maybe"),
        VALID_PRODUCT_IDS,
    ) == "Invalid availability"


def test_platform_normalization():
    assert normalize_platform("Blinkit") == 1
    assert normalize_platform(" blinkit ") == 1
    assert normalize_platform("ZEpto") == 2


def test_price_normalization():
    assert normalize_price("68") == 68.0
    assert normalize_price("₹68") == 68.0
    assert normalize_price(" 68.00 ") == 68.0


def test_availability_normalization():
    assert normalize_availability("true") is True
    assert normalize_availability("false") is False


def test_product_name_normalization():
    from data_pipeline.price_processing import normalize_product_name

    assert normalize_product_name("  Amul   Taaza Milk ") == "amul taaza milk"


def test_timestamp_normalization():
    from data_pipeline.price_processing import normalize_timestamp

    assert normalize_timestamp(
        "2026-10-01T10:00:00Z"
    ) == "2026-10-01T10:00:00Z"


def test_quantity_normalization():
    from data_pipeline.price_processing import normalize_quantity

    assert normalize_quantity(" 500 ") == 500.0
    assert normalize_quantity("-10") is None


def test_unit_normalization():
    from data_pipeline.price_processing import normalize_unit

    assert normalize_unit("grams") == "g"
    assert normalize_unit("KG") == "kg"
    assert normalize_unit("pieces") == "pcs"


def test_unavailable_product_has_no_price():
    assert validate_price_record(
        make_record(
            available="false",
            price="",
        ),
        VALID_PRODUCT_IDS,
    ) is None


def test_missing_required_field_rejected():
    record = make_record()
    del record["timestamp"]

    assert validate_price_record(
        record,
        VALID_PRODUCT_IDS,
    ) == "Missing required field(s): timestamp"


def test_duplicate_detection():
    from data_pipeline.price_processing import detect_duplicates

    records = [
        make_record(),
        make_record(),
        make_record(
            timestamp="2026-10-01T11:00:00Z"
        ),
    ]

    assert detect_duplicates(records) == [2]


def test_multiple_valid_records():
    from data_pipeline.price_processing import process_price_data

    records = [
        make_record(),
        make_record(
            product_id="2",
            product_name="Aashirvaad Atta",
            price="265",
            quantity="5",
            unit="kg",
        ),
    ]

    clean, rejected = process_price_data(
        records,
        VALID_PRODUCT_IDS,
    )

    assert len(clean) == 2
    assert len(rejected) == 0


def test_mixed_valid_and_invalid_records():
    from data_pipeline.price_processing import process_price_data

    records = [
        make_record(),
        make_record(product_id="999"),
        make_record(platform="Unknown"),
    ]

    clean, rejected = process_price_data(
        records,
        VALID_PRODUCT_IDS,
    )

    assert len(clean) == 1
    assert len(rejected) == 2
