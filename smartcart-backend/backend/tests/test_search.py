def test_search_valid_query(client):
    response = client.get("/api/products/search?q=milk")
    assert response.status_code == 200
    data = response.get_json()
    assert data["query"] == "milk"
    assert data["count"] == len(data["products"])
    assert any("Milk" in p["name"] for p in data["products"])


def test_search_case_insensitive(client):
    response = client.get("/api/products/search?q=MILK")
    assert response.status_code == 200
    assert response.get_json()["count"] >= 1


def test_search_matches_brand(client):
    response = client.get("/api/products/search?q=tata")
    assert response.status_code == 200
    data = response.get_json()
    assert data["count"] >= 2  # Tata Salt, Tata Tea


def test_search_empty_query(client):
    response = client.get("/api/products/search?q=")
    assert response.status_code == 400
    assert response.get_json()["error"]["code"] == "EMPTY_SEARCH_QUERY"


def test_search_missing_query(client):
    response = client.get("/api/products/search")
    assert response.status_code == 400
    assert response.get_json()["error"]["code"] == "EMPTY_SEARCH_QUERY"


def test_search_whitespace_only_query(client):
    response = client.get("/api/products/search?q=%20%20")
    assert response.status_code == 400
    assert response.get_json()["error"]["code"] == "EMPTY_SEARCH_QUERY"


def test_search_no_results_is_200_not_error(client):
    response = client.get("/api/products/search?q=zzzznotarealproduct")
    assert response.status_code == 200
    data = response.get_json()
    assert data["products"] == []
    assert data["count"] == 0


def test_search_query_too_long(client):
    response = client.get("/api/products/search?q=" + "a" * 101)
    assert response.status_code == 400
    assert response.get_json()["error"]["code"] == "INVALID_PARAMETER"


def test_search_route_not_confused_with_product_id(client):
    # /api/products/search must never be routed as /api/products/<id>
    response = client.get("/api/products/search?q=tea")
    assert response.status_code == 200
    data = response.get_json()
    assert "query" in data
