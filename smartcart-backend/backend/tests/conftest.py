"""
These tests exercise the real Flask app against a real MySQL database.
Before running `pytest`, make sure you have:

  1. Created the `smartcart` database and run schema.sql against it.
  2. Run `python seed.py` so the demo data from data/*.csv is loaded.
  3. A working .env (copied from .env.example) with correct DB credentials.

No live server needs to be running - Flask's test client calls the app
in-process.
"""

from dotenv import load_dotenv

load_dotenv()

import pytest  # noqa: E402

from app import create_app  # noqa: E402


@pytest.fixture()
def client():
    app = create_app()
    app.config.update(TESTING=True)
    with app.test_client() as test_client:
        yield test_client
