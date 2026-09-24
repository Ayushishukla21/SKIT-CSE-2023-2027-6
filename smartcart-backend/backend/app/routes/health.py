"""
GET /api/health

This is the one endpoint that does NOT use the standard
{"error": {...}} envelope (see API_CONTRACT.md 3.1) - it always returns
its own status object, with HTTP 200 or 503.
"""

from flask import Blueprint, jsonify

from app.db.connection import get_connection

health_bp = Blueprint("health", __name__)


@health_bp.route("/health", methods=["GET"])
def health():
    try:
        conn = get_connection()
        conn.ping(reconnect=False, attempts=1, delay=0)
        conn.close()
        return (
            jsonify(
                {
                    "status": "ok",
                    "service": "smartcart-api",
                    "database": "connected",
                    "contract_version": "1.0",
                }
            ),
            200,
        )
    except Exception:
        # Any failure to connect/ping MySQL means "disconnected" - never
        # leak the underlying exception (host/user/password) to the client.
        return (
            jsonify(
                {
                    "status": "error",
                    "service": "smartcart-api",
                    "database": "disconnected",
                    "contract_version": "1.0",
                }
            ),
            503,
        )
