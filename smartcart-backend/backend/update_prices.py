"""
Runs the price-monitoring update workflow from a prices CSV
(same columns as data/prices.csv; optional `observed_at` column or `updated_at`).

    python update_prices.py [path/to/prices.csv]

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


if __name__ == "__main__":
    sys.exit(main(*sys.argv[1:2]))
