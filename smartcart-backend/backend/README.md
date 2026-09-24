# SmartCart AI – Backend

Flask + MySQL backend implementing `docs/API_CONTRACT.md` v1.0 exactly.
Frozen contracts (`API_CONTRACT.md`, `DATA_SCHEMA.md`) are not modified by
this code — if the two ever disagree, the contract file wins.

## 1. Requirements

- Python 3.10+
- MySQL Server 8.x running locally
- (Optional) MySQL Workbench / any GUI client — not required, everything
  below uses the `mysql` command line client.

## 2. Setup (Windows)

Open PowerShell or Command Prompt in the `backend/` folder.

```bat
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```

## 2b. Setup (macOS / Linux)

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

## 3. Configure environment variables

```bat
copy .env.example .env
```
(macOS/Linux: `cp .env.example .env`)

Open `.env` and set `DB_PASSWORD` (and `DB_USER` if you don't use `root`).
Never commit the real `.env` file.

## 4. Create the database and load the schema

```bat
mysql -u root -p -e "CREATE DATABASE IF NOT EXISTS smartcart;"
mysql -u root -p smartcart < schema.sql
```

This creates `platforms`, `products`, `prices`, `offers` and seeds the
fixed platform rows (Blinkit=1, Zepto=2, Instamart=3, Flipkart Minutes=4).

## 5. Load demo data

```bat
python seed.py
```

This reads `data/products.csv`, `data/prices.csv`, `data/offers.csv`
(identical to the demo rows in `docs/DATA_SCHEMA.md`) and loads them into
MySQL. Safe to re-run any time.

## 6. Run the API

```bat
python run.py
```

The API is now at `http://localhost:5000`. Try:

```bat
curl http://localhost:5000/api/health
curl http://localhost:5000/api/products
curl http://localhost:5000/api/products/1
curl "http://localhost:5000/api/products/search?q=milk"
curl http://localhost:5000/api/products/1/compare
```

## 7. Run tests

Keep the database seeded (server doesn't need to be running — pytest
calls the Flask app in-process):

```bat
pytest
```

To manually check the `/api/health` 503 case, stop MySQL and hit
`/api/health` again — it should return `503` with `"database": "disconnected"`.

## 8. Connecting the frontend

In the frontend's `.env`:

```
VITE_USE_MOCK=false
VITE_API_BASE_URL=http://localhost:5000
```

CORS is already configured to allow `http://localhost:5173` (Vite) and
`http://localhost:3000`.

## Project structure

```
backend/
  app/
    __init__.py        # Flask app factory, CORS, error handlers
    routes/
      health.py         # GET /api/health
      products.py        # GET /api/products, /<id>, /search, /<id>/compare
    services/
      product_service.py     # product list/detail + shared number helpers
      search_service.py       # GET /api/products/search
      comparison_service.py   # GET /api/products/<id>/compare
    db/
      connection.py       # mysql-connector-python connection helper
    utils/
      errors.py           # ApiError + one factory per error code
      validators.py        # page/per_page/id/q validation
  tests/                  # pytest, run against a seeded local MySQL DB
  data/                   # demo CSVs (mirrors docs/DATA_SCHEMA.md)
  schema.sql               # MySQL schema + platform seed
  seed.py                  # loads data/*.csv into MySQL
  requirements.txt
  .env.example
  pytest.ini
  run.py
```

## Scope

Implemented: the 5 contract endpoints, standard error envelope, JSON
404/405 handlers, CORS, comparison sorting/summary rules, contract tests.

Not implemented (future milestones, by design): ML prediction,
recommendations, budget planner, chatbot, notifications, Azure deployment,
payments, advanced scraping.
