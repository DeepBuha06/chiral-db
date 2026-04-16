# JSON Query Language

ChiralDB relies on a declarative JSON instruction set for executing CRUD operations. You never write SQL. You specify the logical fields you want, and the `CrudQueryBuilder` AST parser generates the PostgreSQL queries dynamically.

---

## 1. READ Operations

Read operations retrieve data. You can select fields natively, even if they were autonomously migrated to a child table or a JSONB overflow column.

```json
{
  "operation": "read",
  "session_id": "experiment_01",
  "select": ["username", "device", "events.event_type"],
  "filters": [
    {"field": "events.y", "op": "gte", "value": 500}
  ],
  "limit": 10
}
```

### Supported Filter Operators
| Operator | Description | Example SQL translation |
|----------|-------------|-------------------------|
| `eq`     | Equals      | `field = :val` |
| `neq`    | Not Equals  | `field != :val` |
| `gt`     | Greater Than| `field > :val` |
| `gte`    | Greater/Eq  | `field >= :val` |
| `lt`     | Less Than   | `field < :val` |
| `lte`    | Less/Eq     | `field <= :val` |
| `contains`| JSONB array| `overflow_data @> :val::jsonb` |

---

## 2. CREATE Operations

Create operations bypass the staging buffer and attempt to synchronously insert data into the permanent tables using the currently inferred schema.

```json
{
  "operation": "create",
  "payload": {
    "session_id": "experiment_01",
    "username": "bob",
    "temperature": 25,
    "comments": [{"text": "Hello"}]
  }
}
```
*Note: If the nested `comments` entity has a known schema, it will be inserted into `chiral_data_comments` synchronously. If not, the engine gracefully enqueues the payload to the async worker for schema evolution!*

---

## 3. UPDATE Operations

Logical updates allow you to mutate specific fields. 

!!! success "JSONB Safety"
    If you update a field that resides in the `overflow_data` JSONB column, ChiralDB translates the update into an atomic `jsonb_set(COALESCE(...))` SQL command. This prevents "Lost Updates" during high concurrency.

```json
{
  "operation": "update",
  "session_id": "experiment_01",
  "updates": {
    "temperature": 26,
    "device.os": "Linux"
  },
  "filters": [
    {"field": "username", "op": "eq", "value": "bob"}
  ]
}
```

---

## 4. DELETE Operations

Deletes remove the parent record. Because ChiralDB enforces `ON DELETE CASCADE` foreign keys on dynamically generated child tables, all related nested data is purged simultaneously.

```json
{
  "operation": "delete",
  "session_id": "experiment_01",
  "filters": [
    {"field": "username", "op": "eq", "value": "bob"}
  ]
}
```
