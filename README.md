# Chiral DB

Session-scoped, self-adaptive hybrid database middleware.

## Overview

Chiral is a middleware library that abstracts physical storage. It accepts raw JSON streams and autonomously routes fields to either PostgreSQL (stable, structured data) or MongoDB (volatile, sparse data) based on Shannon Entropy analysis. It provides a unified object-oriented view of this hybrid data to the application layer.

## Project Status

**Alpha.** Core architecture definition phase.

## Prerequisites

*   Python 3.14+
*   uv (Project Manager)
*   Docker & Docker Compose (for local development databases)
*   Just (Command Runner) - Optional but recommended

## Quick Start

1.  **Install dependencies:**
    ```sh
    uv sync
    ```

2.  **Setup pre-commit hooks (CRITICAL):**
    ```sh
    uv run pre-commit install
    ```

3.  **Start local databases:**
    ```sh
    docker compose up -d
    ```

## Development Workflow

We use a strict "Gold Standard" quality pipeline.

### Commands

If you have `just` installed:

*   `just setup`: Install all dependencies and hooks.
*   `just verify`: Run the full QA suite (Formatter -> Linter -> Type Checker -> Tests).
*   `just test`: Run tests with coverage.

Manual equivalents:

*   **Format:** `uv run ruff format .`
*   **Lint:** `uv run ruff check . --fix`
*   **Type Check:** `uv run ty check`
*   **Test:** `uv run pytest`

### Commit Policy

1.  **Pre-commit:** Hooks will run automatically on `git commit`. If they fail, fix the issues and re-add the files.
2.  **Pull Requests:** Direct pushes to `main` are discouraged. Use PRs. CI will enforce all checks.

## Architecture Layers

*   **Layer 1 (Logical):** Client-side decorators (`@chiral_model`).
*   **Layer 2 (Intelligence):** Ingestion buffer, Entropy observer, Router.
*   **Layer 3 (Storage):** Adapters for PostgreSQL and MongoDB.
*   **Metadata:** Persistent mapping of `(session, field) -> (backend, column)`.

## License

MIT. See `LICENSE` file.
