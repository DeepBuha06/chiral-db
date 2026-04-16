# ChiralDB

**ChiralDB** is an autonomous, session-scoped database framework that transparently bridges the gap between Relational (SQL) and Document (JSONB) paradigms over a single PostgreSQL instance.

Instead of defining strict schemas or maintaining a separate MongoDB cluster for unstructured data, ChiralDB completely abstracts storage placement, schema evolution, and SQL JOINs away from the developer.

📚 **[Read the Full Documentation](https://devansh-lodha.github.io/chiral-db/)**

---

## ⚡ Key Features

* **Zero Schema Definition:** Ingest raw JSON. ChiralDB uses Shannon Entropy to autonomously infer data types and split repeating arrays into highly normalized SQL tables.
* **Hybrid Storage Engine:** Flat, stable scalars go to SQL columns. Drift-prone, heavily nested, or sparse data gracefully spills over into `JSONB` automatically.
* **Logical Session Isolation:** Data is physically stored in the same tables, but logically separated by `session_id`.
* **ACID Transactions:** No Two-Phase Commit (2PC) overhead. By utilizing PostgreSQL's JSONB alongside relational tables with `begin_nested()`, we achieve perfect Atomicity and Isolation across paradigms.
* **Built-in Dashboard:** Ships with a React SPA to visualize your logical schemas and execute CRUD operations.

---

## 🛠️ Quick Start

### Installation
```bash
pip install chiral-db
```

### Start the Server & Dashboard
ChiralDB ships with a built-in FastAPI server and React Dashboard. Just provide your PostgreSQL credentials in a `.env` file and run:
```bash
chiral serve --port 8000
```
Open `http://localhost:8000` in your browser to access the interactive Query Executor.

### Programmatic Usage
You can use ChiralDB natively in your Python `asyncio` applications. You don't write DDL. You don't write SQL. You just use data.

```python
import asyncio
from chiral.client import ChiralClient

async def main():
    async with ChiralClient("postgresql+asyncpg://user:pass@localhost:5432/db") as db:
        
        # 1. Ingest arbitrary, schema-less data
        await db.ingest(
            session_id="experiment_01", 
            data={
                "username": "devansh", 
                "sensors": [{"type": "temp", "val": 22}, {"type": "humid", "val": 40}]
            }
        )
        
        # 2. Query it logically. ChiralDB handles the SQL Joins and JSONB unpacking!
        result = await db.query({
            "operation": "read",
            "session_id": "experiment_01",
            "select": ["username", "sensors.val"],
            "filters": [{"field": "sensors.val", "op": "gt", "value": 20}]
        })
        
        print(result["rows"])

if __name__ == "__main__":
    asyncio.run(main())
```

---

## 📄 License
This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
```

### Step 3: Update PyPI with the new README
Because PyPI packages are immutable, you must bump the version number to push the new README to the website.
1. Open `pyproject.toml` and change `version = "1.0.0"` to `version = "1.0.1"`.
2. Rebuild and publish:
   ```bash
   uv build
   uv publish
   ```
*(Go check your package on PyPI right after this—it will look incredible!)*

### Step 4: Push to GitHub & Deploy the Website
MkDocs has a magical built-in command that automatically compiles your documentation into HTML and pushes it to a special `gh-pages` branch on your GitHub repository. GitHub then hosts this branch for free!

**1. Update `repo_url` in `mkdocs.yml`**
Open `mkdocs.yml` and update the `repo_url` at the top to point to your actual GitHub repository:
```yaml
repo_url: https://github.com/your-username/chiral-db
```

**2. Commit and Push your code to GitHub:**
```bash
git add .
git commit -m "feat: Finalize PyPI package, README, and MkDocs setup"
git push origin main
```

**3. Deploy the Website:**
Run this single command in your terminal:
```bash
uv run mkdocs gh-deploy --force
```
*(This command builds the site and pushes it to the `gh-pages` branch on GitHub).*

**4. Turn on GitHub Pages:**
1. Go to your repository on **GitHub.com**.
2. Click on the **Settings** tab.
3. Click on **Pages** in the left sidebar.
4. Under "Build and deployment", set the **Source** to **Deploy from a branch**.
5. Under "Branch", select **`gh-pages`** and click **Save**.

Wait about 60 seconds, and your website will be live at `https://<your-username>.github.io/chiral-db/`! Make sure to update the placeholder link in your `README.md` to point to the real URL.

Let me know when the site is live! You have officially completed the entire lifecycle of a production-grade software project!