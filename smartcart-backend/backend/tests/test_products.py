def test_list_products_default(client):
    response = client.get("/api/products")
    assert response.status_code == 200
    data = response.get_json()
    assert "products" in data and "pagination" in data
    assert data["pagination"]["page"] == 1
    assert data["pagination"]["per_page"] == 20
    assert data["pagination"]["total"] == 6  # demo dataset has 6 products


def test_list_products_pagination(client):
    response = client.get("/api/products?page=1&per_page=2")
    assert response.status_code == 200
    data = response.get_json()
    assert len(data["products"]) == 2
    assert data["pagination"]["per_page"] == 2
    assert data["pagination"]["total_pages"] == 3


def test_list_products_category_filter(client):
    response = client.get("/api/products?category=Dairy")
    assert response.status_code == 200
    data = response.get_json()
    assert len(data["products"]) >= 1
    for product in data["products"]:
        assert product["category"] == "Dairy"


def test_list_products_invalid_page(client):
    response = client.get("/api/products?page=abc")
    assert response.status_code == 400
    assert response.get_json()["error"]["code"] == "INVALID_PARAMETER"


def test_list_products_per_page_out_of_range(client):
    response = client.get("/api/products?per_page=999")
    assert response.status_code == 400
    assert response.get_json()["error"]["code"] == "INVALID_PARAMETER"


def test_get_product_valid(client):
    response = client.get("/api/products/1")
    assert response.status_code == 200
    data = response.get_json()
    assert data["product"]["id"] == 1
    assert data["product"]["name"] == "Amul Taaza Milk"
    assert data["product"]["unit"] == "L"


def test_get_product_invalid_id_non_numeric(client):
    response = client.get("/api/products/abc")
    assert response.status_code == 400
    assert response.get_json()["error"]["code"] == "INVALID_PRODUCT_ID"


def test_get_product_invalid_id_zero(client):
    response = client.get("/api/products/0")
    assert response.status_code == 400
    assert response.get_json()["error"]["code"] == "INVALID_PRODUCT_ID"


def test_get_product_invalid_id_negative(client):
    response = client.get("/api/products/-3")
    assert response.status_code == 400
    assert response.get_json()["error"]["code"] == "INVALID_PRODUCT_ID"


def test_get_product_not_found(client):
    response = client.get("/api/products/9999")
    assert response.status_code == 404
    assert response.get_json()["error"]["code"] == "PRODUCT_NOT_FOUND"


def test_route_not_found(client):
    response = client.get("/api/does-not-exist")
    assert response.status_code == 404
    assert response.get_json()["error"]["code"] == "ROUTE_NOT_FOUND"


def test_method_not_allowed(client):
    response = client.post("/api/products")
    assert response.status_code == 405
    assert response.get_json()["error"]["code"] == "METHOD_NOT_ALLOWED"


def test_cors_allows_configured_origin(client):
    response = client.get("/api/products", headers={"Origin": "http://localhost:5173"})
    assert response.headers.get("Access-Control-Allow-Origin") == "http://localhost:5173"
