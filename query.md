# Query Guide (`/query/translate` and `/query/execute`)

This file documents how to query Chiral DB using JSON requests.

## Endpoints

- `POST /query/translate`
  - Returns generated SQL + bind params only.
- `POST /query/execute`
  - Returns SQL + params + data (`rows`) for reads, or `affected_rows` for writes.

Base URL (local): `http://127.0.0.1:8000`

---

## Request Shape

```json
{
  "operation": "read | create | update | delete",
  "table": "chiral_data",
  "select": ["username", "comments.score"],
  "filters": [
    {"field": "session_id", "op": "eq", "value": "session_assignment_2"}
  ],
  "payload": {},
  "updates": {},
  "limit": 10,
  "offset": 0
}
```

Use only the fields needed for the selected operation.

---

## Filter Operators

Supported operators:

- `eq`
- `ne`
- `gt`
- `gte`
- `lt`
- `lte`
- `contains` (for `overflow_data.<key>` paths)

Example filter item:

```json
{"field": "temperature", "op": "gt", "value": 25}
```

---

## 1) Read Queries

### A. Read from parent SQL columns

```json
{
  "operation": "read",
  "table": "chiral_data",
  "select": ["username", "sys_ingested_at"],
  "filters": [
    {"field": "session_id", "op": "eq", "value": "session_assignment_2"}
  ],
  "limit": 5
}
```

### B. Read parent JSONB key

```json
{
  "operation": "read",
  "table": "chiral_data",
  "select": ["username", "overflow_data.metadata"],
  "filters": [
    {"field": "session_id", "op": "eq", "value": "session_assignment_2"}
  ],
  "limit": 5
}
```

### C. Join-inferred child projection (automatic)

```json
{
  "operation": "read",
  "table": "chiral_data",
  "select": ["username", "comments.score", "comments.is_flagged"],
  "filters": [
    {"field": "session_id", "op": "eq", "value": "session_assignment_2"}
  ],
  "limit": 5
}
```

### D. Join-inferred child typed filters (automatic)

```json
{
  "operation": "read",
  "table": "chiral_data",
  "select": ["username", "comments.score", "comments.is_flagged"],
  "filters": [
    {"field": "session_id", "op": "eq", "value": "session_assignment_2"},
    {"field": "comments.score", "op": "gte", "value": "0.5"},
    {"field": "comments.is_flagged", "op": "eq", "value": "true"}
  ],
  "limit": 10
}
```

Note:
- Child typed filter values can be provided as strings (for example, `"0.5"`, `"true"`); query logic coerces them using inferred child column types.

### E. Child JSONB nested filter path

```json
{
  "operation": "read",
  "table": "chiral_data",
  "select": ["username", "comments.overflow_data.meta"],
  "filters": [
    {"field": "session_id", "op": "eq", "value": "session_assignment_2"},
    {"field": "comments.overflow_data.score", "op": "gte", "value": 0.5}
  ],
  "limit": 10
}
```

---

## 2) Create Query

```json
{
  "operation": "create",
  "table": "chiral_data",
  "payload": {
    "session_id": "session_assignment_2",
    "username": "new_user",
    "sys_ingested_at": 1742643301.25,
    "t_stamp": 1742643301.25,
    "overflow_data": "{}"
  }
}
```

---

## 3) Update Query

```json
{
  "operation": "update",
  "table": "chiral_data",
  "updates": {
    "username": "renamed_user"
  },
  "filters": [
    {"field": "session_id", "op": "eq", "value": "session_assignment_2"},
    {"field": "username", "op": "eq", "value": "new_user"}
  ]
}
```

---

## 4) Delete Query

```json
{
  "operation": "delete",
  "table": "chiral_data",
  "filters": [
    {"field": "session_id", "op": "eq", "value": "session_assignment_2"},
    {"field": "username", "op": "eq", "value": "renamed_user"}
  ]
}
```

---

## cURL Examples

### Translate only

```bash
curl -X POST http://127.0.0.1:8000/query/translate \
  -H "Content-Type: application/json" \
  -d '{
    "operation": "read",
    "table": "chiral_data",
    "select": ["username", "comments.score"],
    "filters": [{"field": "session_id", "op": "eq", "value": "session_assignment_2"}],
    "limit": 5
  }'
```

### Translate + execute

```bash
curl -X POST http://127.0.0.1:8000/query/execute \
  -H "Content-Type: application/json" \
  -d '{
    "operation": "read",
    "table": "chiral_data",
    "select": ["username", "comments.score", "comments.is_flagged"],
    "filters": [
      {"field": "session_id", "op": "eq", "value": "session_assignment_2"},
      {"field": "comments.score", "op": "gte", "value": "0.5"}
    ],
    "limit": 10
  }'
```

---

## Common Mistakes

- Using `contains` on non-JSONB fields.
- Using non-numeric filter values for numeric range operations on JSONB paths.
- Misspelling filter operator names (`gte` not `=>`, `eq` not `=`).
