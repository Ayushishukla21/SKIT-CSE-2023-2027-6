"""
Loads the DEMO historical prices (data/raw/historical_prices_raw.csv, made by
the data pipeline) into the price_history table. Safe to run many times:
rows that already exist are skipped. This is demo data, not live data.

    python load_history.py
"""

import csv
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

from app.db.connection import get_connection  # noqa: E402

CSV_PATH = Path(__file__).resolve().parents[2] / "data" / "raw" / "historical_prices_raw.csv"


def main():
    with open(CSV_PATH, newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))

    conn = get_connection()
    cur = conn.cursor()
    added = 0
    for r in rows:
        available = r["available"].strip().lower() == "true"
        price = r["price"].strip() or None
        if not available:
            price = None
        recorded = r["recorded_at"].replace("T", " ").replace("Z", "")
        cur.execute(
            "INSERT IGNORE INTO price_history "
            "(product_id, platform_id, price, currency, available, recorded_at) "
            "VALUES (%s, %s, %s, %s, %s, %s)",
            (int(r["product_id"]), int(r["platform_id"]), price,
             r["currency"] or "INR", available, recorded),
        )
        added += cur.rowcount
    conn.commit()
    cur.close()
    conn.close()
    print(f"Read {len(rows)} rows, added {added} new rows to price_history (demo data).")


if __name__ == "__main__":
    main()
