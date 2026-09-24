"""
Every error response in this API (except /api/health) uses the shape
defined in API_CONTRACT.md section 2.3:

    { "error": { "code": "...", "message": "..." } }

ApiError carries the HTTP status code alongside the code/message so a
single Flask error handler (see app/__init__.py) can turn any of these
into the correct JSON response.
"""


class ApiError(Exception):
    def __init__(self, code, message, status_code):
        super().__init__(message)
        self.code = code
        self.message = message
        self.status_code = status_code

    def to_dict(self):
        return {"error": {"code": self.code, "message": self.message}}


# --- Factory helpers -------------------------------------------------
# One helper per error code from API_CONTRACT.md section 4, so routes and
# services raise these instead of hard-coding strings everywhere.

def invalid_product_id(message="Product ID must be a positive integer"):
    return ApiError("INVALID_PRODUCT_ID", message, 400)


def product_not_found(message="Product not found"):
    return ApiError("PRODUCT_NOT_FOUND", message, 404)


def empty_search_query(message="Search query must not be empty"):
    return ApiError("EMPTY_SEARCH_QUERY", message, 400)


def invalid_parameter(message="Invalid parameter"):
    return ApiError("INVALID_PARAMETER", message, 400)


def database_error(message="Database error. Please try again later"):
    return ApiError("DATABASE_ERROR", message, 503)


def internal_server_error(message="Something went wrong"):
    return ApiError("INTERNAL_SERVER_ERROR", message, 500)


def route_not_found(message="The requested URL was not found"):
    return ApiError("ROUTE_NOT_FOUND", message, 404)


def method_not_allowed(message="This HTTP method is not allowed for this route"):
    return ApiError("METHOD_NOT_ALLOWED", message, 405)
