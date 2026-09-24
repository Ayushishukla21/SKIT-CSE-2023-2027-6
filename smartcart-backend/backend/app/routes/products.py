"""
GET /api/products
GET /api/products/<id>
GET /api/products/search?q=<query>
GET /api/products/<id>/compare

The /search route is declared before the /<raw_id> route in this file for
readability. Flask/Werkzeug already prefers the static "search" segment
over the dynamic <raw_id> segment regardless of declaration order, but
<raw_id> is still validated manually in validators.py so a bad value like
/api/products/abc returns the JSON INVALID_PRODUCT_ID error rather than a
generic 404.
"""

from flask import Blueprint, jsonify, request

from app.services import comparison_service, product_service, search_service
from app.utils.validators import validate_pagination, validate_product_id, validate_search_query

products_bp = Blueprint("products", __name__)


@products_bp.route("/products", methods=["GET"])
def list_products():
    page, per_page = validate_pagination(request.args.get("page"), request.args.get("per_page"))
    category = request.args.get("category") or None
    result = product_service.get_products(page, per_page, category)
    return jsonify(result), 200


@products_bp.route("/products/search", methods=["GET"])
def search_products():
    query, limit = validate_search_query(request.args.get("q"), request.args.get("limit"))
    result = search_service.search_products(query, limit)
    return jsonify(result), 200


@products_bp.route("/products/<raw_id>", methods=["GET"])
def get_product(raw_id):
    product_id = validate_product_id(raw_id)
    product = product_service.get_product_by_id(product_id)
    return jsonify({"product": product}), 200


@products_bp.route("/products/<raw_id>/compare", methods=["GET"])
def compare_product(raw_id):
    product_id = validate_product_id(raw_id)
    result = comparison_service.get_comparison(product_id)
    return jsonify(result), 200
