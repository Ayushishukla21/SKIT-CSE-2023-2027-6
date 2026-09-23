# SmartCart AI – Data Schema (CSV Contract)

**Version:** 1.0 (matches API_CONTRACT.md 1.0) – FROZEN
**Audience:** Ayushi (produces the files), Chahak (loads them into MySQL)

The CSV files are the bridge between the data pipeline and the API. Column names are **identical** to the MySQL column names and, where possible, to the API field names, so nothing has to be renamed on the way.

---

## 1. File rules (apply to all CSV files)

- Encoding **UTF-8**, comma separated, first row is the header.
- Column names are exactly as listed below (lowercase snake_case, same order).
- Empty value = `NULL` (leave the cell blank, do not write `null`, `NA`, or `-`).
- Booleans are written as lowercase `true` or `false`.
- Prices use a dot for decimals: `65.00` (no `₹`, no commas).
- Timestamps are ISO 8601 UTC: `2026-09-01T10:00:00Z`.
- No duplicate IDs. IDs are never changed or reused once shared.
- Text has no leading or trailing spaces.

---

## 2. `platforms` (fixed seed – not a CSV from Ayushi)

Seeded by the backend `schema.sql`. Do not change.

| id | name |
|---|---|
| 1 | Blinkit |
| 2 | Zepto |
| 3 | Instamart |
| 4 | Flipkart Minutes |

---

## 3. `products.csv`

| Column | Type | Required | Rules |
|---|---|---|---|
| `id` | integer | yes | Unique, positive |
| `name` | string (max 150) | yes | Name **without** pack size |
| `brand` | string (max 80) | yes | |
| `category` | string | yes | `Dairy`, `Staples`, `Beverages`, `Snacks`, `Packaged Food` |
| `quantity` | decimal | yes | Greater than 0, e.g. `1`, `250`, `5` |
| `unit` | string | yes | `g`, `kg`, `ml`, `L`, `pcs` |
| `image_url` | string | no | Blank for now |

Use the unit as printed on the pack (`1 L` stays `1` + `L`; do not silently convert `1000 ml` to `1 L`). Matching different spellings of the same product is a later step (matching service) and will use its own data.

**Demo rows**

```csv
id,name,brand,category,quantity,unit,image_url
1,Amul Taaza Milk,Amul,Dairy,1,L,
2,Aashirvaad Atta,Aashirvaad,Staples,5,kg,
3,Tata Salt,Tata,Staples,1,kg,
4,Tata Tea,Tata,Beverages,250,g,
5,Maggi 2-Minute Noodles,Maggi,Packaged Food,70,g,
6,Parle-G Biscuits,Parle,Snacks,250,g,
```

---

## 4. `prices.csv`

One **current** price per product per platform in this milestone.

| Column | Type | Required | Rules |
|---|---|---|---|
| `product_id` | integer | yes | Must exist in `products.csv` |
| `platform_id` | integer | yes | 1 to 4 |
| `price` | decimal (2 dp) | see rule | Greater than 0. **Blank if `available` is `false`.** |
| `currency` | string | yes | Always `INR` |
| `available` | boolean | yes | `true` / `false` |
| `updated_at` | timestamp | yes | ISO 8601 UTC |

Unique key: (`product_id`, `platform_id`). No duplicate pairs.

The `price` is the **final selling price including any offer** (see API contract 2.2).

**Demo rows (all DEMO values, not real prices)**

```csv
product_id,platform_id,price,currency,available,updated_at
1,1,68.00,INR,true,2026-09-01T10:00:00Z
1,2,65.00,INR,true,2026-09-01T10:00:00Z
1,3,70.00,INR,true,2026-09-01T10:00:00Z
1,4,67.00,INR,true,2026-09-01T10:00:00Z
2,1,265.00,INR,true,2026-09-01T10:00:00Z
2,2,259.00,INR,true,2026-09-01T10:00:00Z
2,3,272.00,INR,true,2026-09-01T10:00:00Z
2,4,262.00,INR,true,2026-09-01T10:00:00Z
3,1,28.00,INR,true,2026-09-01T10:00:00Z
3,2,27.00,INR,true,2026-09-01T10:00:00Z
3,3,29.00,INR,true,2026-09-01T10:00:00Z
3,4,28.00,INR,true,2026-09-01T10:00:00Z
4,1,145.00,INR,true,2026-09-01T10:00:00Z
4,2,142.00,INR,true,2026-09-01T10:00:00Z
4,3,148.00,INR,true,2026-09-01T10:00:00Z
4,4,,INR,false,2026-09-01T10:00:00Z
5,1,14.00,INR,true,2026-09-01T10:00:00Z
5,2,14.00,INR,true,2026-09-01T10:00:00Z
5,3,15.00,INR,true,2026-09-01T10:00:00Z
5,4,14.00,INR,true,2026-09-01T10:00:00Z
6,1,25.00,INR,true,2026-09-01T10:00:00Z
6,2,24.00,INR,true,2026-09-01T10:00:00Z
6,3,24.00,INR,true,2026-09-01T10:00:00Z
6,4,26.00,INR,true,2026-09-01T10:00:00Z
```

Product 4 on Flipkart Minutes is deliberately unavailable, so both teams test the unavailable case. Product 6 has a tie at ₹24 (Zepto and Instamart), so the tie rule (smaller `platform_id` wins → Zepto) gets tested.

---

## 5. `offers.csv`

Optional extra info shown next to a price. At most **one active offer** per (`product_id`, `platform_id`) in this milestone.

| Column | Type | Required | Rules |
|---|---|---|---|
| `id` | integer | yes | Unique, positive |
| `product_id` | integer | yes | Must exist in `products.csv` |
| `platform_id` | integer | yes | 1 to 4 |
| `title` | string (max 100) | yes | Short text, e.g. `Flat ₹10 off` |
| `description` | string | no | |
| `discount_amount` | decimal (2 dp) | no | Rupees, ≥ 0 |
| `is_active` | boolean | yes | Only `true` rows appear in the API |

**Demo rows**

```csv
id,product_id,platform_id,title,description,discount_amount,is_active
1,2,1,Flat ₹10 off,,10.00,true
2,6,3,Save ₹2,,2.00,true
```

---

## 6. Mapping: CSV → MySQL → API

| API field | MySQL | Source |
|---|---|---|
| `product.id` | `products.id` | `products.csv` `id` |
| `product.name/brand/category/quantity/unit/image_url` | same column names | `products.csv` |
| `prices[].platform_id` | `prices.platform_id` | `prices.csv` |
| `prices[].platform` | `platforms.name` | join on `platform_id` |
| `prices[].price/currency/available` | same column names | `prices.csv` |
| `prices[].offer` | `offers.*` | active row from `offers.csv`, else `null` |
| `meta.last_updated` | `MAX(prices.updated_at)` | computed |
| `summary.*` | not stored | computed by `comparison_service.py` |

`summary` (lowest, highest, saving, best platform) is **never** stored in CSV or MySQL. The backend calculates it every time so it can never go out of sync.

---

## 7. Validation checklist for Ayushi (before handing over files)

- [ ] Headers match exactly
- [ ] No duplicate `id` in products / offers, no duplicate (`product_id`, `platform_id`) in prices
- [ ] Every `product_id` in prices/offers exists in products
- [ ] Every `platform_id` is 1 to 4
- [ ] `unit` and `category` are from the allowed lists
- [ ] `price` is blank when `available=false`, and > 0 otherwise
- [ ] Booleans are `true`/`false`, timestamps are ISO 8601 UTC
- [ ] File opens cleanly as UTF-8 (the `₹` sign in offers is preserved)

## 8. Later (not in this milestone)

`price_history`, `users`, `recommendations`, `alerts`, `budgets`, and product alias/matching data will get their own contracts when those modules start. The current schema is designed so they can be added without changing any file above.
