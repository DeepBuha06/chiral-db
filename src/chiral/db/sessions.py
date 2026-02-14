# Copyright (c) 2026 Chiral Contributors
#
# This source code is licensed under the MIT license found in the
# LICENSE file in the root directory of this source tree.

"""Database session management."""

from collections.abc import Callable
from functools import wraps
from typing import Any

from sqlalchemy.ext.asyncio import async_sessionmaker

from chiral.db.connection import get_mongo_client, get_sql_engine


def session(func: Callable[..., Any]) -> Callable[..., Any]:
    """Provide independent database sessions to the decorated function.

    Args:
        func: The async function to decorate.

    Lifecycle:
    - Creates new Mongo Client and SQL Engine per call.
    - Disposes/Closes them after execution.
    - Commits SQL transaction on success, Rollbacks on exception.

    """

    @wraps(func)
    async def wrapper(*args: object, **kwargs: object) -> object:
        # Create independent connections
        mongo_client = get_mongo_client()
        sql_engine = get_sql_engine()

        # Create SQL Session factory
        session_local = async_sessionmaker(bind=sql_engine, expire_on_commit=False)

        mongo_db = mongo_client.chiral  # Accessing 'chiral' database

        async with session_local() as sql_session:
            try:
                # Inject dependencies
                kwargs["mongo_db"] = mongo_db
                kwargs["sql_session"] = sql_session

                result = await func(*args, **kwargs)

                await sql_session.commit()
            except Exception:
                await sql_session.rollback()
                raise
            else:
                return result
            finally:
                # Cleanup resources ensures independence
                await sql_engine.dispose()
                mongo_client.close()

    return wrapper
