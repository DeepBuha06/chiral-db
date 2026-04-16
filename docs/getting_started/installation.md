# Installation & Setup

ChiralDB is published on PyPI and can be installed like any standard Python package. 

!!! warning "Prerequisites"
    ChiralDB requires **Python 3.11+** and a running **PostgreSQL** instance. It uses `asyncpg` under the hood for maximum asynchronous performance.

---

## 1. Install the Package

You can install ChiralDB using `pip`, `uv`, or your preferred package manager:

=== "uv (Recommended)"
    ```bash
    uv pip install chiral-db
    ```

=== "pip"
    ```bash
    pip install chiral-db
    ```

---

## 2. Configure the Database

ChiralDB needs to know how to connect to your PostgreSQL instance. It reads configuration from environment variables (or a `.env` file in your working directory).

Create a `.env` file and add your PostgreSQL credentials:

```env title=".env"
POSTGRES_USER=postgres
POSTGRES_PASSWORD=mysecretpassword
POSTGRES_DB=chiral_db
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
```

!!! tip "Using Docker"
    If you don't have PostgreSQL installed locally, you can easily spin one up using Docker:
    ```bash
    docker run --name chiral-postgres -e POSTGRES_USER=postgres -e POSTGRES_PASSWORD=mysecretpassword -e POSTGRES_DB=chiral_db -p 5432:5432 -d postgres:17
    ```

---

## 3. Start the Server

ChiralDB comes with a built-in FastAPI wrapper that hosts the REST API and the React Dashboard UI. You don't need to write any code to start it!

Just run the CLI command:

```bash
chiral serve --port 8000
```

You should see output indicating that Uvicorn is running:
```text
Starting ChiralDB Server on port 8000...
INFO:     Started server process [12345]
INFO:     Waiting for application startup.
INFO:     Application startup complete.
INFO:     Uvicorn running on http://0.0.0.0:8000 (Press CTRL+C to quit)
```

**Congratulations!** Your autonomous database framework is now online. 

Next, head over to the [**Dashboard UI**](dashboard.md) guide to learn how to visualize your data!
