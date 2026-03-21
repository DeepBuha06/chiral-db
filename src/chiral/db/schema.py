# Copyright (c) 2026 Chiral Contributors
#
# This source code is licensed under the MIT license found in the
# LICENSE file in the root directory of this source tree.

"""Database initialization and schema definitions."""

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


async def init_metadata_table(session: AsyncSession) -> None:
    """Ensure the session metadata table exists."""
    sql = """
    CREATE TABLE IF NOT EXISTS session_metadata (
        session_id TEXT PRIMARY KEY,
        record_count INTEGER DEFAULT 0,
        status TEXT DEFAULT 'collecting',
        schema_json TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """
    await session.execute(text(sql))

    # Main data table with overflow_data JSONB column (replaces MongoDB permanent collection)
    # System columns:
    # - username: Traceability field (mandatory)
    # - sys_ingested_at: Server timestamp (bi-temporal, join key)
    # - t_stamp: Client timestamp (bi-temporal)
    # - overflow_data: JSONB column for nested/unstructured data (replaces MongoDB)
    sql_data = """
    CREATE TABLE IF NOT EXISTS chiral_data (
        id SERIAL PRIMARY KEY,
        session_id TEXT,
        username TEXT,
        sys_ingested_at FLOAT,
        t_stamp FLOAT,
        overflow_data JSONB DEFAULT '{}'::jsonb
    );
    """
    await session.execute(text(sql_data))

    # Staging table with JSONB column (replaces MongoDB staging collection)
    sql_staging = """
    CREATE TABLE IF NOT EXISTS staging_data (
        id SERIAL PRIMARY KEY,
        session_id TEXT,
        data JSONB NOT NULL
    );
    """
    await session.execute(text(sql_staging))

    await session.commit()
