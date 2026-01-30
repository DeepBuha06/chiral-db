set shell := ["bash", "-c"]

# Install dependencies and setup environment
setup:
    uv sync --all-extras --dev
    uv run pre-commit install

# Run all checks (Format, Lint, Type, Test)
verify: format lint type test
    @echo "✅ All checks passed!"

# Format code (Ruff)
format:
    uv run ruff format .

# Lint code (Ruff)
lint:
    uv run ruff check . --fix

# Type check (Ty)
type:
    uv run ty check

# Run tests (Pytest)
test:
    uv run pytest --cov=src --cov-report=term-missing

# Start database containers
up:
    docker compose up -d

# Stop database containers
down:
    docker compose down

# Clean temporary files
clean:
    rm -rf .ruff_cache .pytest_cache .coverage htmlcov dist build
    find . -type d -name "__pycache__" -exec rm -rf {} +
