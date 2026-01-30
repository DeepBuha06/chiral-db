# Copyright (c) 2026 Chiral Contributors
#
# This source code is licensed under the MIT license found in the
# LICENSE file in the root directory of this source tree.

"""Tests for the configuration module."""

import pytest
from pydantic import ValidationError

from src.chiral.config import Settings


def test_settings_validation_success(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test that settings load correctly with valid environment variables."""
    monkeypatch.setenv("POSTGRES_USER", "user")
    monkeypatch.setenv("POSTGRES_PASSWORD", "pass")
    monkeypatch.setenv("POSTGRES_DB", "db")
    monkeypatch.setenv("MONGO_INITDB_ROOT_USERNAME", "root")
    monkeypatch.setenv("MONGO_INITDB_ROOT_PASSWORD", "rootpass")

    settings = Settings()
    assert settings.POSTGRES_USER == "user"
    assert settings.database_url == "postgresql+asyncpg://user:pass@localhost:5432/db"
    assert settings.mongo_url == "mongodb://root:rootpass@localhost:27017"


def test_settings_validation_failure() -> None:
    """Test that missing required fields raise a ValidationError."""
    # Ensure no env vars are set (or at least the required ones are missing)
    # We rely on the defaults being empty strings which trigger our validator
    with pytest.raises(ValidationError) as excinfo:
        Settings(
            POSTGRES_USER="",
            POSTGRES_PASSWORD="",
            POSTGRES_DB="",
            MONGO_INITDB_ROOT_USERNAME="",
            MONGO_INITDB_ROOT_PASSWORD="",
        )
    assert "Missing required environment variables" in str(excinfo.value)
