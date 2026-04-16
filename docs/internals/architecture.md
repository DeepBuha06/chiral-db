# Architecture

ChiralDB relies on a single PostgreSQL instance to manage both structured and unstructured data, ensuring ACID compliance without the overhead of distributed Two-Phase Commits.

### 1. The Staging Buffer
Incoming records are initially dumped into a high-speed `staging_data` table using a `JSONB` column. 

### 2. Autonomous Normalization Engine
Once a session hits 100 records, the Background Worker analyzes the data:
* **Shannon Entropy** calculates type stability. Stable scalars (`int`, `str`, `bool`) are mapped to native PostgreSQL columns.
* **Repeating Entities** are detected. Homogeneous arrays of objects are stripped out and materialized into dynamic child tables (e.g., `chiral_data_comments`) with Foreign Keys back to the parent table.

### 3. The Query Compiler
When a user issues a logical read, the `CrudQueryBuilder` AST parser dynamically generates a `LEFT JOIN` across the dynamically generated child tables and utilizes `jsonb_extract_path_text` for overflow fields, returning a perfectly reconstructed JSON object.