# Copyright (c) 2026 Chiral Contributors
#
# This source code is licensed under the MIT license found in the
# LICENSE file in the root directory of this source tree.

"""Verify database connections script."""

import asyncio
import logging
import sys

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

from src.chiral.config import get_settings

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


async def check_sql() -> None:
    """Check PostgreSQL connection."""
    settings = get_settings()
    logger.info("Connecting to PostgreSQL at port %s...", settings.POSTGRES_PORT)
    try:
        engine = create_async_engine(settings.database_url)
        async with engine.connect() as conn:
            result = await conn.execute(text("SHOW server_version;"))
            version = result.scalar()
            logger.info("SUCCESS: PostgreSQL %s connected.", version)
        await engine.dispose()
    except Exception:
        logger.exception("FAILURE: PostgreSQL connection failed.")
        sys.exit(1)


async def main() -> None:
    """Run connection checks."""
    await check_sql()


if __name__ == "__main__":
    asyncio.run(main())
