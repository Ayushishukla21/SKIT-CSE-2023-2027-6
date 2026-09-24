import os

from dotenv import load_dotenv

load_dotenv()  # reads .env before anything touches DB_* env vars

from app import create_app  # noqa: E402  (import after load_dotenv on purpose)

app = create_app()

if __name__ == "__main__":
    debug = os.getenv("FLASK_DEBUG", "true").lower() == "true"
    app.run(host="0.0.0.0", port=5000, debug=debug)
