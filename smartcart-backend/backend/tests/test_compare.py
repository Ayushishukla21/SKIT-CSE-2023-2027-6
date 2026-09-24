def test_compare_basic_shape(client):
    response = client.get("/api/products/1/compare")
    assert response.status_code == 200
    data = response.get_json()
    assert data["product"]["id"] == 1
    assert "prices" in data and "summary" in data and "meta" in data
    assert data["meta"]["data_source"] == "demo"


def test_compare_available_platforms_come_first(client):
    response = client.get("/api/products/1/compare")
    data = response.get_json()
    availabilities = [p["available"] for p in data["prices"]]
    # All True values must come before all False values
    assert availabilities == sorted(availabilities, key=lambda a: a is False)


def test_compare_cheapest_first_among_available(client):
    response = client.get("/api/products/1/compare")
    data = response.get_json()
    available_prices = [p["price"] for p in data["prices"] if p["available"]]
    assert available_prices == sorted(available_prices)


def test_compare_unavailable_platform_has_null_price(client):
    # Product 4 = Tata Tea, deliberately unavailable on Flipkart Minutes (id 4)
    response = client.get("/api/products/4/compare")
    assert response.status_code == 200
    data = response.get_json()
    flipkart = next(p for p in data["prices"] if p["platform_id"] == 4)
    assert flipkart["available"] is False
    assert flipkart["price"] is None


def test_compare_tie_breaking_by_platform_id(client):
    # Product 6 = Parle-G, tied at 24 on Zepto (2) and Instamart (3) -> Zepto wins
    response = client.get("/api/products/6/compare")
    assert response.status_code == 200
    data = response.get_json()
    assert data["summary"]["best_platform"] == "Zepto"
    assert data["summary"]["lowest_price"] == 24.0


def test_compare_saving_calculation(client):
    response = client.get("/api/products/1/compare")
    data = response.get_json()
    summary = data["summary"]
    if summary["lowest_price"] is not None:
        expected = round(summary["highest_price"] - summary["lowest_price"], 2)
        assert summary["potential_saving"] == expected


def test_compare_offer_attached_when_present(client):
    # Product 2 = Aashirvaad Atta, has an active offer on Blinkit (platform_id 1)
    response = client.get("/api/products/2/compare")
    data = response.get_json()
    blinkit = next(p for p in data["prices"] if p["platform_id"] == 1)
    assert blinkit["offer"] is not None
    assert blinkit["offer"]["title"] == "Flat ₹10 off"
    assert blinkit["offer"]["discount_amount"] == 10.0


def test_compare_invalid_id(client):
    response = client.get("/api/products/abc/compare")
    assert response.status_code == 400
    assert response.get_json()["error"]["code"] == "INVALID_PRODUCT_ID"


def test_compare_not_found(client):
    response = client.get("/api/products/9999/compare")
    assert response.status_code == 404
    assert response.get_json()["error"]["code"] == "PRODUCT_NOT_FOUND"
