# Python Client API

The `ChiralClient` is the primary entry point for interacting with ChiralDB programmatically. It manages the underlying PostgreSQL connection pool (`asyncpg`) and securely orchestrates background schema migrations.

---

## Initialization

You should instantiate `ChiralClient` as an asynchronous context manager. This ensures database connections are cleanly acquired and disposed of, and guarantees that background migration tasks finish executing before the application exits.

```python
from chiral.client import ChiralClient

async with ChiralClient("postgresql+asyncpg://user:pass@localhost/db") as db:
    # use the db client
    pass
```

---

## Core Methods

### `ingest(session_id: str, data: dict)`
Ingests a single JSON record into the database. 
If the session reaches the `INITIAL_ANALYSIS_THRESHOLD` (100 records), this method automatically spawns an asynchronous background task to infer the schema and migrate the data from staging into permanent structured tables.

* **Returns:** `dict` containing the ingestion status, current record count, and a flag indicating if a background worker was triggered.

```python
await db.ingest(
    session_id="exp_01", 
    data={"username": "alice", "temperature": 22.5}
)
```

### `query(request: dict)`
Translates and executes a logical JSON CRUD request against the database. It handles SQL table joins and `JSONB` path extractions autonomously.

* **Returns:** `dict` containing the executed SQL, bound parameters, and the resulting `rows` (for READ operations) or `affected_rows` (for write operations).

```python
result = await db.query({
    "operation": "read",
    "session_id": "exp_01",
    "select": ["username", "temperature"]
})
```

### `flush(session_id: str)`
Forces the staging queue to immediately flush into the permanent tables. If the schema has not been inferred yet, this will force a synchronous analysis and migration phase.

* **Returns:** `dict` containing the number of flushed records.

```python
await db.flush("exp_01")
```

### `get_logical_schema(session_id: str)`
Retrieves a flat list of all inferred logical fields for a given session. This includes dotted paths for nested entities (e.g., `comments.text`).

* **Returns:** `list[str]` of field names.

```python
fields = await db.get_logical_schema("exp_01")
print(fields) # ["username", "temperature", "comments", "comments.text"]
```