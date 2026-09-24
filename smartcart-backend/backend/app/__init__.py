from flask import Flask, jsonify
from flask_cors import CORS

from app.routes.health import health_bp
from app.routes.products import products_bp
from app.utils.errors import ApiError, method_not_allowed, route_not_found


def create_app():
    app = Flask(__name__)

    # CORS - local frontend dev origins only (API_CONTRACT.md 1 / section 18)
    CORS(
        app,
        resources={
            r"/api/*": {
                "origins": [
                    "http://localhost:5173",
                    "http://localhost:3000",
                ]
            }
        },
    )

    app.register_blueprint(health_bp, url_prefix="/api")
    app.register_blueprint(products_bp, url_prefix="/api")

    @app.errorhandler(ApiError)
    def handle_api_error(err):
        return jsonify(err.to_dict()), err.status_code

    @app.errorhandler(404)
    def handle_404(_err):
        return jsonify(route_not_found().to_dict()), 404

    @app.errorhandler(405)
    def handle_405(_err):
        return jsonify(method_not_allowed().to_dict()), 405

    @app.errorhandler(Exception)
    def handle_unexpected(err):
        # ApiError, 404 and 405 are handled by the more specific handlers
        # above; Flask/Werkzeug dispatches to those first. Anything that
        # reaches here is a genuine bug - log it, but never leak details
        # (stack trace, SQL, secrets) to the client.
        if isinstance(err, ApiError):
            return handle_api_error(err)
        app.logger.exception("Unhandled exception")
        return (
            jsonify({"error": {"code": "INTERNAL_SERVER_ERROR", "message": "Something went wrong"}}),
            500,
        )

    return app
