"""
Thin wrapper around mysql-connector-python.

Every route/service opens its own short-lived connection with
get_connection() and closes it when done. This keeps things simple and
beginner-friendly (no connection pool to reason about) while still being
safe for a small demo API.
"""

import os

import mysql.connector


def get_db_config():
    return {
        "host": os.getenv("DB_HOST", "localhost"),
        "port": int(os.getenv("DB_PORT", "3306")),
        "database": os.getenv("DB_NAME", "smartcart"),
        "user": os.getenv("DB_USER", "root"),
        "password": os.getenv("DB_PASSWORD", ""),
        "connection_timeout": 5,
    }


def get_connection():
    """
    Opens a new MySQL connection.

    Raises mysql.connector.Error if MySQL is unreachable or credentials are
    wrong. Callers are expected to catch that and turn it into a
    DATABASE_ERROR (503) API response - they must never let the raw
    exception (with host/user/password details) reach the client.
    """
    config = get_db_config()
    return mysql.connector.connect(**config)
