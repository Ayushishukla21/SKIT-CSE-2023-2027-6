# SmartCart AI – API Contract

**Contract version:** 1.0
**Milestone:** 10 Aug 2026 → 21 Sep 2026
**Status:** FROZEN – approved. Changes only through the change process in section 7.

This file is the **single source of truth** for how the Flask backend (Chahak) and the React frontend (Abhay) talk to each other. Ayushi's data files feed the database, so they follow `docs/DATA_SCHEMA.md`, which is built to match this file.

If the code and this file disagree, **this file wins** and the code is fixed.

---

## 1. Global rules

| Rule | Value |
|---|---|
| Base URL (local dev) | `http://localhost:5000` |
| All routes start with | `/api` |
| Format | JSON only, UTF-8, `Content-Type: application/json` |
| Field naming | **snake_case everywhere** (`lowest_price`, never `lowestPrice`) |
| Methods | All endpoints are `GET` only in this milestone. No request bodies. |
| Currency | Always `"INR"`. Prices are JSON numbers (never strings), max 2 decimals. Frontend adds the `₹` sign. |
| Null values | Fields are always present. If there is no value, the field is `null` (it is never left out). |
| Field order | Not guaranteed. Frontend must read fields by name. |
| CORS | Backend allows `http://localhost:5173` (Vite) and `http://localhost:3000` in dev. |
| Data source | All data in this milestone is **DEMO data**. The compare response says so in `meta.data_source`. |

### Fixed platform IDs (never change)

| platform_id | platform (exact string) |
|---|---|
| 1 | `Blinkit` |
| 2 | `Zepto` |
| 3 | `Instamart` |
| 4 | `Flipkart Minutes` |

### Allowed `unit` values

`g`, `kg`, `ml`, `L`, `pcs`

Case matters: it is `L` (capital), and `g`, `kg`, `ml`, `pcs` are lowercase.

### Allowed `category` values (current milestone)

`Dairy`, `Staples`, `Beverages`, `Snacks`, `Packaged Food`

---

## 2. Shared object shapes

### 2.1 Product object

```json
{
  "id": 1,
  "name": "Amul Taaza Milk",
  "brand": "Amul",
  "category": "Dairy",
  "quantity": 1,
  "unit": "L",
  "image_url": null
}
```

| Field | Type | Required | Notes |
|---|---|---|---|
| `id` | integer | yes | Stable product ID. Never reused. |
| `name` | string | yes | Product name **without** the pack size (`"Amul Taaza Milk"`, not `"Amul Taaza Milk 1L"`). |
| `brand` | string | yes | e.g. `"Amul"` |
| `category` | string | yes | One of the allowed categories. |
| `quantity` | number | yes | Pack size number, e.g. `1`, `500`, `5`. |
| `unit` | string | yes | One of the allowed units. |
| `image_url` | string or null | yes | `null` for now; frontend shows a placeholder. |

The frontend builds the display label itself: `name + " " + quantity + unit` → "Amul Taaza Milk 1L".

### 2.2 Offer object (or `null`)

```json
{
  "title": "Flat ₹10 off",
  "description": null,
  "discount_amount": 10.0
}
```

| Field | Type | Required | Notes |
|---|---|---|---|
| `title` | string | yes | Short text to show on the card. |
| `description` | string or null | yes | Optional longer text. |
| `discount_amount` | number or null | yes | Rupees saved. Informational only. |

> **Important:** `price` in a price entry is **already the final price the customer pays, offer included.** The offer is only extra information for the UI. Never subtract `discount_amount` from `price` again.

### 2.3 Error object

Every error, from every endpoint, has exactly this shape:

```json
{
  "error": {
    "code": "PRODUCT_NOT_FOUND",
    "message": "Product not found"
  }
}
```

| Field | Type | Notes |
|---|---|---|
| `error.code` | string | Machine-readable, UPPER_SNAKE_CASE. Frontend uses this in `if` checks. |
| `error.message` | string | Human-readable, safe to show. Never contains stack traces, SQL, or passwords. |

---

## 3. Endpoints

### 3.1 `GET /api/health`

Checks that the backend is running and MySQL is reachable.

- **Parameters:** none

**Success – 200 (backend running, MySQL reachable)**

```json
{
  "status": "ok",
  "service": "smartcart-api",
  "database": "connected",
  "contract_version": "1.0"
}
```

**Database failure – 503 (backend running, MySQL not reachable)**

```json
{
  "status": "error",
  "service": "smartcart-api",
  "database": "disconnected",
  "contract_version": "1.0"
}
```

| Field | Type | Required | Allowed values |
|---|---|---|---|
| `status` | string | yes | `"ok"` or `"error"` |
| `service` | string | yes | always `"smartcart-api"` |
| `database` | string | yes | `"connected"` or `"disconnected"` |
| `contract_version` | string | yes | `"1.0"` |

> **Note:** `/api/health` is the one endpoint that does **not** use the standard `{"error": {...}}` format. Its failure response is the health object above, with HTTP `503`. Every other endpoint uses the standard error format.

---

### 3.2 `GET /api/products`

Returns a page of products.

**Query parameters (all optional)**

| Name | Type | Default | Rules |
|---|---|---|---|
| `page` | integer | `1` | Must be ≥ 1 |
| `per_page` | integer | `20` | 1 to 50 |
| `category` | string | none | Exact match on an allowed category |

Products are sorted by `id` ascending.

**Success – 200**

```json
{
  "products": [
    {
      "id": 1,
      "name": "Amul Taaza Milk",
      "brand": "Amul",
      "category": "Dairy",
      "quantity": 1,
      "unit": "L",
      "image_url": null
    }
  ],
  "pagination": {
    "page": 1,
    "per_page": 20,
    "total": 6,
    "total_pages": 1
  }
}
```

| Field | Type | Required |
|---|---|---|
| `products` | array of Product | yes (empty array `[]` if none) |
| `pagination.page` | integer | yes |
| `pagination.per_page` | integer | yes |
| `pagination.total` | integer | yes |
| `pagination.total_pages` | integer | yes |

**Errors**

| HTTP | code | When |
|---|---|---|
| 400 | `INVALID_PARAMETER` | `page` / `per_page` is not a valid integer or is out of range |
| 503 | `DATABASE_ERROR` | MySQL failure |
| 500 | `INTERNAL_SERVER_ERROR` | Any unexpected error |

---

### 3.3 `GET /api/products/<id>`

Returns one product.

**Path parameter**

| Name | Type | Rules |
|---|---|---|
| `id` | integer | Positive whole number |

**Success – 200**

```json
{
  "product": {
    "id": 1,
    "name": "Amul Taaza Milk",
    "brand": "Amul",
    "category": "Dairy",
    "quantity": 1,
    "unit": "L",
    "image_url": null
  }
}
```

**Errors**

| HTTP | code | When | Example `message` |
|---|---|---|---|
| 400 | `INVALID_PRODUCT_ID` | `<id>` is not a positive integer (`abc`, `0`, `-3`, `1.5`) | `"Product ID must be a positive integer"` |
| 404 | `PRODUCT_NOT_FOUND` | Valid ID but no such product | `"Product not found"` |
| 503 | `DATABASE_ERROR` | MySQL failure | `"Database error. Please try again later"` |
| 500 | `INTERNAL_SERVER_ERROR` | Unexpected error | `"Something went wrong"` |

---

### 3.4 `GET /api/products/search?q=<query>`

Searches products by name, brand, or category.

**Query parameters**

| Name | Type | Required | Rules |
|---|---|---|---|
| `q` | string | yes | Trimmed. Must not be empty. Max 100 characters. Case-insensitive. |
| `limit` | integer | no | Default `20`, range 1 to 50 |

**Success – 200 (results found)**

```json
{
  "query": "milk",
  "products": [
    {
      "id": 1,
      "name": "Amul Taaza Milk",
      "brand": "Amul",
      "category": "Dairy",
      "quantity": 1,
      "unit": "L",
      "image_url": null
    }
  ],
  "count": 1
}
```

| Field | Type | Required | Notes |
|---|---|---|---|
| `query` | string | yes | The trimmed query that was searched |
| `products` | array of Product | yes | Best matches first |
| `count` | integer | yes | Equals `products.length` |

**Success – 200 (no results)**

```json
{
  "query": "xyzabc",
  "products": [],
  "count": 0
}
```

> **Decision – "no search results" is NOT an HTTP error.** Searching for something that does not exist is a normal situation, so the backend returns `200` with an empty list, and the frontend shows the `EmptyState` component when `count === 0`. The code `NO_SEARCH_RESULTS` is **reserved and never returned** in this milestone.

**Errors**

| HTTP | code | When | Example `message` |
|---|---|---|---|
| 400 | `EMPTY_SEARCH_QUERY` | `q` missing, empty, or only spaces | `"Search query must not be empty"` |
| 400 | `INVALID_PARAMETER` | `q` longer than 100 characters, or `limit` invalid | `"Search query is too long"` |
| 503 | `DATABASE_ERROR` | MySQL failure | `"Database error. Please try again later"` |
| 500 | `INTERNAL_SERVER_ERROR` | Unexpected error | `"Something went wrong"` |

> **Backend note:** `/api/products/search` and `/api/products/<id>` overlap. Register the search route so that the word `search` is never treated as a product ID. Validate `<id>` manually (as a string) so that `/api/products/abc` returns the JSON `INVALID_PRODUCT_ID` error, not Flask's default HTML 404.

---

### 3.5 `GET /api/products/<id>/compare`

Compares one product's price across all platforms.

**Path parameter:** `id` – same rule as 3.3.

**Success – 200**

```json
{
  "product": {
    "id": 1,
    "name": "Amul Taaza Milk",
    "brand": "Amul",
    "category": "Dairy",
    "quantity": 1,
    "unit": "L",
    "image_url": null
  },
  "prices": [
    {
      "platform_id": 2,
      "platform": "Zepto",
      "price": 65.0,
      "currency": "INR",
      "available": true,
      "offer": null
    },
    {
      "platform_id": 4,
      "platform": "Flipkart Minutes",
      "price": 67.0,
      "currency": "INR",
      "available": true,
      "offer": null
    },
    {
      "platform_id": 1,
      "platform": "Blinkit",
      "price": 68.0,
      "currency": "INR",
      "available": true,
      "offer": null
    },
    {
      "platform_id": 3,
      "platform": "Instamart",
      "price": 70.0,
      "currency": "INR",
      "available": true,
      "offer": null
    }
  ],
  "summary": {
    "lowest_price": 65.0,
    "highest_price": 70.0,
    "potential_saving": 5.0,
    "best_platform": "Zepto"
  },
  "meta": {
    "data_source": "demo",
    "last_updated": "2026-09-01T10:00:00Z"
  }
}
```

**Price entry fields**

| Field | Type | Required | Notes |
|---|---|---|---|
| `platform_id` | integer | yes | 1 to 4 (see table above) |
| `platform` | string | yes | Exact platform name |
| `price` | number or null | yes | `null` only when `available` is `false` |
| `currency` | string | yes | Always `"INR"` |
| `available` | boolean | yes | `false` = platform does not currently list/stock it |
| `offer` | Offer or null | yes | See 2.2 |

**Summary fields**

| Field | Type | Required | Notes |
|---|---|---|---|
| `lowest_price` | number or null | yes | Minimum `price` among `available: true` entries |
| `highest_price` | number or null | yes | Maximum `price` among `available: true` entries |
| `potential_saving` | number or null | yes | `highest_price − lowest_price`, rounded to 2 decimals |
| `best_platform` | string or null | yes | Platform with `lowest_price`. On a tie, the platform with the smaller `platform_id`. |

**Meta fields**

| Field | Type | Required | Notes |
|---|---|---|---|
| `data_source` | string | yes | `"demo"` in this milestone. The UI must show a "Demo data" label. Later may become `"live"`. |
| `last_updated` | string or null | yes | ISO 8601 UTC timestamp (latest price update), `null` if no prices |

> **The backend owns all comparison logic.** The frontend must NOT calculate or re-derive `lowest_price`, `highest_price`, `potential_saving`, or `best_platform`, and must not re-sort `prices`. It only displays what the API returns.

**Ordering rules (backend does this, frontend does not re-sort)**

1. Available platforms first, cheapest → most expensive.
2. Ties are ordered by `platform_id` ascending.
3. Unavailable platforms (`available: false`) come last, ordered by `platform_id`.

**Summary rules**

- Only `available: true` prices count. Unavailable platforms are ignored.
- If only **one** platform is available: `lowest_price == highest_price`, `potential_saving` is `0.0`.
- If **no** platform is available or the product has no price rows: `prices` may be `[]` or all unavailable, and `lowest_price`, `highest_price`, `potential_saving`, `best_platform` are all `null`. This is still HTTP `200`.

**Example with an unavailable platform and an offer**

```json
{
  "platform_id": 4,
  "platform": "Flipkart Minutes",
  "price": null,
  "currency": "INR",
  "available": false,
  "offer": null
}
```

```json
{
  "platform_id": 1,
  "platform": "Blinkit",
  "price": 265.0,
  "currency": "INR",
  "available": true,
  "offer": {
    "title": "Flat ₹10 off",
    "description": null,
    "discount_amount": 10.0
  }
}
```

**Errors**

| HTTP | code | When |
|---|---|---|
| 400 | `INVALID_PRODUCT_ID` | `<id>` is not a positive integer |
| 404 | `PRODUCT_NOT_FOUND` | No such product |
| 503 | `DATABASE_ERROR` | MySQL failure |
| 500 | `INTERNAL_SERVER_ERROR` | Unexpected error |

---

## 4. Error code master list

| HTTP | code | Meaning |
|---|---|---|
| 400 | `INVALID_PRODUCT_ID` | Product ID is not a positive integer |
| 400 | `EMPTY_SEARCH_QUERY` | `q` missing or blank |
| 400 | `INVALID_PARAMETER` | Any other bad query parameter |
| 404 | `PRODUCT_NOT_FOUND` | Valid ID, product does not exist |
| 404 | `ROUTE_NOT_FOUND` | URL does not exist (JSON, not HTML) |
| 405 | `METHOD_NOT_ALLOWED` | Wrong HTTP method (JSON, not HTML) |
| 503 | `DATABASE_ERROR` | MySQL unreachable or query failed |
| 500 | `INTERNAL_SERVER_ERROR` | Anything unexpected |
| – | `NO_SEARCH_RESULTS` | **Reserved, not used.** Empty search returns 200 (see 3.4). |

Adding a **new** error code later is allowed. Renaming or removing an existing one is a breaking change (see section 7).

---

## 5. What the frontend does with each outcome

| Outcome | UI component |
|---|---|
| Request in progress | `LoadingSpinner` |
| `200` and `count === 0` (search) or `products.length === 0` (list) | `EmptyState` |
| `PRODUCT_NOT_FOUND` | `EmptyState` or `ErrorMessage` with "Product not found" |
| `EMPTY_SEARCH_QUERY` | Prevent the call (disable search on blank input) |
| `DATABASE_ERROR`, `INTERNAL_SERVER_ERROR`, network failure | `ErrorMessage` with a "Try again" button |
| `meta.data_source === "demo"` | Small "Demo data" badge near prices |

`src/services/api.js` must turn every failure into a thrown error carrying `code` and `message`, so pages never parse raw responses.

---

## 6. Frontend `api.js` function names (fixed)

| Function | Calls | Returns (resolved value) |
|---|---|---|
| `getHealth()` | `GET /api/health` | health object |
| `getProducts({ page, per_page, category })` | `GET /api/products` | `{ products, pagination }` |
| `getProductById(id)` | `GET /api/products/<id>` | `{ product }` |
| `searchProducts(query, limit)` | `GET /api/products/search` | `{ query, products, count }` |
| `compareProduct(id)` | `GET /api/products/<id>/compare` | `{ product, prices, summary, meta }` |

Rules:

- The resolved values are **exactly** the JSON bodies above. No renaming, no reshaping (no camelCase conversion).
- The mock version of each function returns exactly the same shape as the real one.
- Switching mock → Flask is done with one env variable: `VITE_USE_MOCK=true|false` and `VITE_API_BASE_URL=http://localhost:5000`. Components never import `mockData.js`.

---

## 7. Integration rules

1. **This file is the single source of truth and is FROZEN at version 1.0.** Backend, frontend, and data all follow it.
2. **snake_case only.** No mixing `lowest_price` / `lowestPrice`.
3. **No breaking changes without agreement of all three members.** Breaking = rename/remove a field, change a type, change an error code, change a URL. Adding a **new** field is non-breaking; the frontend must ignore fields it does not know.
4. **Every contract change** requires, in the same pull request: an update to this file, a bump of the version at the top (and `contract_version` in `/api/health`), and a note in `docs/INTEGRATION_NOTES.md`.
5. **Backend owns comparison sorting and summary calculation.** The frontend never computes `lowest_price`, `highest_price`, `potential_saving`, or `best_platform`.
6. **Empty search is a normal result:** HTTP 200 with `products: []`, never an error.
7. **`price` is the final price used for comparison.** Offers are informational only and are never subtracted again.
8. **`meta.data_source`** must always be present so demo data is clearly distinguishable from future live data.
9. **Stable IDs:** product IDs and platform IDs never change or get reused once seeded.
10. **Demo data honesty:** the app must never present demo data as live prices. `meta.data_source` drives the "Demo data" badge.
11. **Mock data = contract.** `mockData.js` must contain the same values as the seed data in `docs/DATA_SCHEMA.md`, in the same shapes.
12. **Contract tests:** the backend has tests that check every response against these field names and types.
13. **No branch crossing:** nobody edits another member's branch. Contract changes come through a PR to `main`, and everyone then merges `main` into their own branch.

---

## 8. Who implements what

| Person | Responsibility |
|---|---|
| **Chahak (backend)** | Implement the 5 endpoints exactly as written, the error format, JSON handlers for 404/405/500, ordering and summary rules, CORS, contract tests. Load seed/CSV data into MySQL. |
| **Abhay (frontend)** | `api.js` with the 5 functions in section 6, `mockData.js` matching section 3 exactly, and pages that handle loading / empty / error / demo-badge states. |
| **Ayushi (data)** | Produce `products.csv`, `prices.csv`, `offers.csv` exactly as in `docs/DATA_SCHEMA.md`. Keep IDs stable and values valid. |
