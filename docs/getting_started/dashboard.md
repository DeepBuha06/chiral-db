# The Dashboard UI

ChiralDB ships with a deeply integrated, interactive React Single Page Application (SPA). The dashboard allows you to explore inferred schemas, monitor session states, and execute CRUD operations without writing a single line of SQL.

If your server is running (`chiral serve`), simply open your browser to:

[**http://localhost:8000**](http://localhost:8000)

---

## 1. Session Context
ChiralDB is a multi-tenant framework. All data is logically isolated by a `session_id`. 

At the top left of the dashboard, you will see the **Session Context** dropdown. 
Selecting a session automatically loads its unique schema and data. Below the dropdown, a status widget displays:

* **Status:** The current phase of the autonomous engine (e.g., `COLLECTING`, `ANALYZING`, `MIGRATED`).
* **Records:** Total number of records ingested in this session.
* **Schema:** The current schema version. (Versions increment automatically if Type Drift or new nested entities are detected).

---

## 2. Entity Inspector
Because ChiralDB dynamically splits arrays into underlying PostgreSQL tables, it can be hard to know what data you actually have. The **Entity Inspector** solves this.

Click **Open Entity Inspector** to view a tree representation of your data. 

!!! success "Logical Abstraction"
    Notice that the inspector hides physical database implementation details. You won't see foreign keys (`chiral_data_id`) or overflow bins (`overflow_data`). You only see your data exactly as you provided it in JSON!

---

## 3. Logical Query Executor
The core feature of the dashboard is the CRUD operations panel.

### 🔍 Read Operations
1. Select **READ**.
2. **Select Fields:** Choose the fields you want to retrieve. You can select parent fields (e.g., `username`) and nested fields (e.g., `comments.text`) simultaneously.
3. **Target Filters:** Add conditions. Behind the scenes, ChiralDB will map these to `WHERE` clauses, automatically coercing types and casting `JSONB` properties safely.
4. Click **Execute READ**.

### ➕ Create Operations
1. Select **CREATE**.
2. Paste raw JSON into the Payload box.
3. Click **Execute CREATE**.
*If the session hasn't hit the 100-record threshold, the record is placed in the high-speed staging queue. You can force the engine to migrate it by clicking the **Flush API** button.*

### ✏️ Update Operations
ChiralDB safely handles logical updates across relational and document boundaries.
1. Select **UPDATE**.
2. Add the fields and new values you wish to change.
3. Provide a filter (e.g., `username = 'alice'`) to target the specific record.
4. Click **Execute UPDATE**.
*Note: The engine translates dotted notation (e.g., `device.os`) into atomic `jsonb_set` commands, ensuring no "Lost Updates" occur during concurrent writes.*

---

## 4. Under the Hood (SQL Details)
Want to see the magic? After executing any query, click the **"View SQL Execution Details"** toggle at the bottom of the result tab.

Here, you can inspect the exact parameterized SQL query ChiralDB generated. You'll see how it seamlessly utilizes `LEFT JOIN`s for repeating entities and `->>` operators for unstructured JSONB data—all from a single logical JSON request!
