## 2. Mandatory Report Questions

### 1. Normalization Strategy
**Q: How did you resolve type naming ambiguities? What rules did you follow to ensure they didn’t create duplicate columns?**

**A:**
*   **Attribute Naming:** Per the instructor's specific clarification for this assignment, we treat casing differences (e.g., `ip` vs `IP` vs `IpAddress`) as **distinct logical attributes**. We do not normalize them into a single column (e.g., `ip_address`). This preserves the exact semantics of the incoming stream.
*   **Type Normalization:** We map disparate Python/JSON value types to standard SQL ISO types:
    *   `int` $\rightarrow$ `INTEGER`
    *   `float` $\rightarrow$ `DOUBLE PRECISION`
    *   `bool` $\rightarrow$ `BOOLEAN`
    *   `str` $\rightarrow$ `TEXT`
*   **Duplicate Prevention:** We enforce a strict **1-to-1 mapping** between a logical attribute key and a physical column. We do *not* create versioned columns (e.g., `age_int`, `age_string`). If a specific attribute key (e.g., `age`) changes type mid-stream (Type Drift), we do not create a second column; instead, we migrate the attribute to MongoDB (see Question 5).

### 2. Placement Heuristics
**Q: What specific thresholds (e.g., frequency %) were used to decide between SQL and MongoDB?**

**A:** We utilize **Shannon Entropy ($H$)** calculated during the analysis phase (first 100 records).
*   **Wheat (SQL):** Fields with $H \approx 0$ (High Type Stability) AND primitive types (`int`, `float`, `bool`).
*   **Chaff (MongoDB):** Fields with $H > 0$ (Mixed Types) OR Complex Structure (`dict`, `list`).
*   **Logic:** Nested structures are *always* routed to MongoDB. Flat fields are routed to SQL only if they maintain type consistency.

### 3. Uniqueness
**Q: How did you identify which fields should be marked as UNIQUE in SQL versus those that are just frequent?**

**A:**
*   **Detection:** During the initial analysis phase (first 100 records), we check if `count(distinct values) == count(total values)`. If true, the column is created with a `UNIQUE` constraint in PostgreSQL.
*   **Adaptation:** If a subsequent insert violates this constraint (due to sample bias), we catch the `IntegrityError`, dynamically **DROP** the unique constraint on that column, and retry the insert. This ensures the system prefers availability over strict constraint enforcement for inferred schemas.

### 4. Value Interpretation
**Q: How did your system differentiate between a string representing an IP ("1.2.3.4") and a float (1.2)?**

**A:** We employ strict Python type inference.
*   The system attempts to cast values in this order: `int` -> `float` -> `bool`.
*   `"1.2"` successfully casts to `float`.
*   `"1.2.3.4"` raises a `ValueError` when casting to `float`, so it falls back to `str`.
*   This inferred type is stored in the metadata map. If a column is defined as `FLOAT` and a `str` arrives later, it triggers a Drift Event.
