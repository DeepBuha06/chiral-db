# Copyright (c) 2026 Chiral Contributors
#
# This source code is licensed under the MIT license found in the
# LICENSE file in the root directory of this source tree.

"""Database connection factories."""

from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine

from chiral.config import get_settings


def get_sql_engine() -> AsyncEngine:
    """Create a new SQLAlchemy AsyncEngine."""
    settings = get_settings()
    return create_async_engine(settings.database_url, echo=False)
