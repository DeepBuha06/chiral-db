# Copyright (c) 2026 Chiral Contributors
#
# This source code is licensed under the MIT license found in the
# LICENSE file in the root directory of this source tree.

"""Configuration settings for the application."""

from functools import lru_cache
from pathlib import Path
from typing import Self

from pydantic import MongoDsn, PostgresDsn, computed_field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # PostgreSQL Configuration
    POSTGRES_USER: str = ""
    POSTGRES_PASSWORD: str = ""
    POSTGRES_DB: str = ""
    POSTGRES_PORT: int = 5432
    POSTGRES_HOST: str = "localhost"

    # MongoDB Configuration
    MONGO_INITDB_ROOT_USERNAME: str = ""
    MONGO_INITDB_ROOT_PASSWORD: str = ""
    MONGO_PORT: int = 27017
    MONGO_HOST: str = "localhost"

    model_config = SettingsConfigDict(
        env_file=Path(__file__).resolve().parent.parent.parent / ".env",
        env_ignore_empty=True,
        extra="ignore",
    )

    @model_validator(mode="after")
    def verify_required_fields(self) -> Self:
        """Ensure all required fields are present and not empty."""
        required_fields = [
            "POSTGRES_USER",
            "POSTGRES_PASSWORD",
            "POSTGRES_DB",
            "MONGO_INITDB_ROOT_USERNAME",
            "MONGO_INITDB_ROOT_PASSWORD",
        ]
        missing = [f for f in required_fields if not getattr(self, f)]
        if missing:
            msg = f"Missing required environment variables: {', '.join(missing)}"
            raise ValueError(msg)
        return self

    @computed_field
    @property
    def database_url(self) -> str:
        """Construct the PostgreSQL database URL."""
        return str(
            PostgresDsn.build(
                scheme="postgresql+asyncpg",
                username=self.POSTGRES_USER,
                password=self.POSTGRES_PASSWORD,
                host=self.POSTGRES_HOST,
                port=self.POSTGRES_PORT,
                path=self.POSTGRES_DB,
            )
        )

    @computed_field
    @property
    def mongo_url(self) -> str:
        """Construct the MongoDB connection URL."""
        return str(
            MongoDsn.build(
                scheme="mongodb",
                username=self.MONGO_INITDB_ROOT_USERNAME,
                password=self.MONGO_INITDB_ROOT_PASSWORD,
                host=self.MONGO_HOST,
                port=self.MONGO_PORT,
            )
        )


@lru_cache
def get_settings() -> Settings:
    """Return a cached instance of the Settings class."""
    return Settings()
