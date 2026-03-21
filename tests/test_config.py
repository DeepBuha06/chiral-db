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

    settings = Settings()
    assert settings.POSTGRES_USER == "user"
    assert settings.database_url == "postgresql+asyncpg://user:pass@localhost:5432/db"


def test_settings_validation_failure() -> None:
    """Test that missing required fields raise a ValidationError."""
    with pytest.raises(ValidationError) as excinfo:
        Settings(
            POSTGRES_USER="",
            POSTGRES_PASSWORD="",
            POSTGRES_DB="",
        )
    assert "Missing required environment variables" in str(excinfo.value)
