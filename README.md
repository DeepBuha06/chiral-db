# Chiral DB

Session-scoped, self-adaptive hybrid database middleware.

## Overview

Chiral is a middleware library that abstracts physical storage. It accepts raw JSON streams and autonomously routes fields to either PostgreSQL (stable, structured data) or MongoDB (volatile, sparse data) based on Shannon Entropy analysis. It provides a unified object-oriented view of this hybrid data to the application layer.

## Project Status

**Alpha.** Core architecture definition phase.

## Prerequisites

*   Python 3.13+
*   uv (Project Manager)
*   Docker & Docker Compose (for local development databases)
*   Just (Command Runner) - **Required**

## Environment Setup

1.  **Clone the repository:**
    ```sh
    git clone https://github.com/devansh-lodha/chiral-db.git
    cd chiral-db
    ```

2.  **Configure Environment Variables:**
    Copy the example configuration file:
    ```sh
    cp .env.example .env
    ```
    The defaults in `.env` (Postgres on port 5432, Mongo on 27017) are designed to work out-of-the-box with the provided Docker Compose setup.

3.  **Install Just:**
    If you don't have `just` installed, install it via your package manager (e.g., `brew install just`).

4.  **Initialize Project:**
    Run the setup recipe to install dependencies and pre-commit hooks:
    ```sh
    just setup
    ```

## Development Workflow

We enforce strict quality standards using automated tooling. All commands are abstracted via `just`.

### Running Services

Start the local PostgreSQL and MongoDB containers:
```sh
just up
```

Stop them:
```sh
just down
```

### Verification & Testing

Before submitting code, ensure all checks pass.

*   **Run All Checks:**
    ```sh
    just verify
    ```
    (Runs Format -> Lint -> Type Check -> Tests)

*   **Run Tests Only:**
    ```sh
    just test
    ```

### Individual Tools

*   **Format:** `just format` (uses `ruff format`)
*   **Lint:** `just lint` (uses `ruff check`)
*   **Type Check:** `just type` (uses `ty check`)

### Commit Policy

1.  **Pre-commit Hooks:** Configured to run automatically on `git commit`. Ensure your environment is set up (`just setup`).
2.  **Pull Requests:** Direct pushes to `main` are discouraged. CI will run the full `just verify` suite on every PR.
3.  **Conventional Commits:** Please follow the [Conventional Commits](https://www.conventionalcommits.org/) specification for your commit messages (e.g., `feat: add ingestion logic`, `fix: resolve db connection timeout`).

## Architecture Layers

*   **Layer 1 (Logical):** Client-side decorators (`@chiral_model`).
*   **Layer 2 (Intelligence):** Ingestion buffer, Entropy observer, Router.
*   **Layer 3 (Storage):** Adapters for PostgreSQL and MongoDB.
*   **Metadata:** Persistent mapping of `(session, field) -> (backend, column)`.

## License

MIT. See `LICENSE` file.
