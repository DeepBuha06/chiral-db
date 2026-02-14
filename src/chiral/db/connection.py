# Copyright (c) 2026 Chiral Contributors
#
# This source code is licensed under the MIT license found in the
# LICENSE file in the root directory of this source tree.

"""Database connection factories."""

from motor.motor_asyncio import AsyncIOMotorClient
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine

from chiral.config import get_settings


def get_mongo_client() -> AsyncIOMotorClient:
    """Create a new MongoDB client."""
    settings = get_settings()
    return AsyncIOMotorClient(settings.mongo_url)


def get_sql_engine() -> AsyncEngine:
    """Create a new SQLAlchemy AsyncEngine."""
    settings = get_settings()
    return create_async_engine(settings.database_url, echo=False)
