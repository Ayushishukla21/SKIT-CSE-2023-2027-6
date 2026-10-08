"""
Runs the price-monitoring update workflow from a prices CSV
(same columns as data/prices.csv; optional `observed_at` column or `updated_at`).

    python update_prices.py [path/to/prices.csv]
    python update_prices.py --demo      # end-to-end history demo (temporary product)

Safe to re-run: repeated identical rows are reported as "unchanged".
"""

import csv
import os
import sys

from dotenv import load_dotenv

load_dotenv()

from app.services.price_monitor_service import update_prices  # noqa: E402
from app.utils.errors import ApiError  # noqa: E402

DEFAULT_CSV = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "prices.csv")


def main(path=DEFAULT_CSV):
    with open(path, newline="", encoding="utf-8") as f:
        records = []
        for row in csv.DictReader(f):
            row["observed_at"] = row.get("observed_at") or row.get("updated_at")
            records.append(row)
    try:
        outcome = update_prices(records)
    except ApiError as err:
        print(f"Aborted: {err.code} - {err.message}")
        return 1
    counts = {}
    for r in outcome["results"]:
        counts[r["status"]] = counts.get(r["status"], 0) + 1
    print(f"Processed {len(records)} records: {counts}, {len(outcome['errors'])} rejected")
    for e in outcome["errors"]:
        print(f"  row {e['index'] + 1}: {e['code']} - {e['message']}")
    return 0


DEMO_PRODUCT_ID = 9999


def demo():
    """
    Walks one price through the whole pipeline using a TEMPORARY product
    (id 9999, removed at the end), so seeded demo data is never touched.
    Prints each step and the resulting history (same data as
    GET /api/products/9999/history while it exists).
    """
    from app.db.connection import get_connection
    from app.services.history_service import get_history
    from app.services.price_monitor_service import update_price

    conn = get_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM products WHERE id = %s", (DEMO_PRODUCT_ID,))
    cur.execute(
        "INSERT INTO products (id, name, brand, category, quantity, unit) "
        "VALUES (%s, 'Demo Product', 'Demo', 'Demo', 1, 'kg')", (DEMO_PRODUCT_ID,))
    conn.commit()

    def rec(price, at, **kw):
        return {"product_id": DEMO_PRODUCT_ID, "platform_id": 1, "price": price,
                "observed_at": at, **kw}

    steps = [
        ("1. incoming price (Rs 1,299.5 normalised)", rec("Rs 1,299.5", "2026-10-01T10:00:00Z")),
        ("2. same data again (idempotent)", rec(1299.5, "2026-10-01T10:00:00Z")),
        ("3. older observation (stale, rejected)", rec(1, "2026-09-30T10:00:00Z")),
        ("4. changed price (new history row)", rec(1250, "2026-10-02T10:00:00Z")),
        ("5. unavailable (price NULL)", rec(None, "2026-10-03T10:00:00Z", available=False)),
        ("6. invalid price (validation)", rec("abc", "2026-10-04T10:00:00Z")),
    ]
    try:
        for label, record in steps:
            try:
                out = update_price(record)
                print(f"{label}: {out['status']} (price={out['price']})")
            except ApiError as err:
                print(f"{label}: rejected {err.code}")
        print("\nHistory:")
        for h in get_history(DEMO_PRODUCT_ID)["history"]:
            print(f"  {h['recorded_at']}  platform {h['platform_id']}  price={h['price']}  available={h['available']}")
    finally:
        cur.execute("DELETE FROM products WHERE id = %s", (DEMO_PRODUCT_ID,))
        conn.commit()
        cur.close()
        conn.close()
    return 0


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--demo":
        sys.exit(demo())
    sys.exit(main(*sys.argv[1:2]))
