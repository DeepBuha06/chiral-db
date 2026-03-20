# Copyright (c) 2026 Chiral Contributors
#
# This source code is licensed under the MIT license found in the
# LICENSE file in the root directory of this source tree.

"""Data Migration Logic."""

import json
import logging
import re
from typing import Any

from sqlalchemy import text
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from chiral.db.sessions import session

logger = logging.getLogger(__name__)


def cast_value(value: object, expected_type: str) -> object:
    """Attempt to cast value to expected type."""
    if value is None:
        return None
    if expected_type == "int":
        return int(value)  # type: ignore[arg-type]
    if expected_type == "float":
        return float(value)  # type: ignore[arg-type]
    if expected_type == "bool":
        if isinstance(value, str):
            return value.lower() in ("true", "1", "yes")
        return bool(value)
    return str(value)


def _ensure_system_columns(existing_columns: list[str]) -> tuple[list[str], list[str]]:
    """Ensure system columns exist and return columns to add and valid SQL columns.

    Returns:
        Tuple of (columns_to_add, valid_sql_cols)

    """
    columns_to_add = []
    valid_sql_cols = []

    if "username" not in existing_columns:
        columns_to_add.append('ADD COLUMN IF NOT EXISTS "username" TEXT')
    valid_sql_cols.append("username")

    if "sys_ingested_at" not in existing_columns:
        columns_to_add.append('ADD COLUMN IF NOT EXISTS "sys_ingested_at" FLOAT UNIQUE')
    valid_sql_cols.append("sys_ingested_at")

    if "t_stamp" not in existing_columns:
        columns_to_add.append('ADD COLUMN IF NOT EXISTS "t_stamp" FLOAT')
    valid_sql_cols.append("t_stamp")

    # Ensure overflow_data JSONB column exists
    if "overflow_data" not in existing_columns:
        columns_to_add.append("ADD COLUMN IF NOT EXISTS \"overflow_data\" JSONB DEFAULT '{}'::jsonb")

    return columns_to_add, valid_sql_cols


def _build_schema_columns(
    analysis: dict[str, Any], existing_columns: list[str], valid_sql_cols: list[str]
) -> list[str]:
    """Build schema columns from analysis.

    Returns:
        List of columns to add

    """
    columns_to_add = []

    for col, meta in analysis.items():
        if col in ["session_id", "sys_ingested_at", "t_stamp", "username"]:
            continue

        if meta["target"] == "sql":
            if col not in existing_columns:
                sql_type = "TEXT"
                if meta["type"] == "int":
                    sql_type = "INTEGER"
                elif meta["type"] == "float":
                    sql_type = "FLOAT"
                elif meta["type"] == "bool":
                    sql_type = "BOOLEAN"

                constraint = "UNIQUE" if meta["unique"] else ""
                columns_to_add.append(f'ADD COLUMN IF NOT EXISTS "{col}" {sql_type} {constraint}')
                valid_sql_cols.append(col)
            elif col in existing_columns:
                valid_sql_cols.append(col)

    return columns_to_add


def _process_document(
    doc: dict[str, Any], session_id: str, analysis: dict[str, Any]
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Process a document for migration, splitting data between SQL columns and JSONB overflow.

    Returns:
        Tuple of (sql_row, overflow_data)

    """
    username = doc.get("username", "unknown")
    sys_ingested_at = doc.get("sys_ingested_at")
    t_stamp = doc.get("t_stamp")

    sql_row = {"session_id": session_id, "username": username}
    overflow = {}

    if sys_ingested_at is not None:
        sql_row["sys_ingested_at"] = sys_ingested_at
    if t_stamp is not None:
        sql_row["t_stamp"] = t_stamp

    for key, value in doc.items():
        if key in ["_id", "session_id", "username", "sys_ingested_at", "t_stamp"]:
            continue

        meta = analysis.get(key)
        target_overflow = True

        if meta and meta["target"] == "sql":
            try:
                casted_val = cast_value(value, meta["type"])
                sql_row[key] = casted_val
                target_overflow = False
            except (ValueError, TypeError):
                target_overflow = True

        if target_overflow:
            overflow[key] = value

    return sql_row, overflow


async def _insert_sql_row(
    sql_row: dict[str, Any],
    overflow: dict[str, Any],
    valid_sql_cols: list[str],
    table_name: str,
    sql_session: AsyncSession,
) -> None:
    """Insert SQL row with overflow_data JSONB column."""
    insert_keys = [k for k in sql_row if k in valid_sql_cols or k == "session_id"]

    if len(insert_keys) == 0:
        return

    # Always include overflow_data
    insert_keys.append("overflow_data")
    sql_row["overflow_data"] = json.dumps(overflow) if overflow else "{}"

    col_list = ", ".join([f'"{k}"' for k in insert_keys])
    bind_list = ", ".join([f":{k}" for k in insert_keys])
    insert_stmt = text('INSERT INTO "' + table_name + '" (' + col_list + ") VALUES (" + bind_list + ")")

    try:
        await sql_session.execute(insert_stmt, sql_row)
    except IntegrityError as e:
        await sql_session.rollback()
        err_msg = str(e.orig) if hasattr(e, "orig") else str(e)
        match = re.search(r"Key \((.*?)\)=", err_msg)

        if match:
            col_culprit = match.group(1).replace('"', "")
            logger.info("Unique constraint violation on column '%s', removing constraint", col_culprit)
            await remove_unique_constraint(sql_session, table_name, col_culprit)

            try:
                await sql_session.execute(insert_stmt, sql_row)
                logger.info("Successfully inserted after removing unique constraint on '%s'", col_culprit)
            except SQLAlchemyError:
                logger.exception("Failed to insert even after removing constraint")
        else:
            logger.warning("Integrity error without identifiable column: %s", err_msg)
    except SQLAlchemyError:
        logger.exception("Unexpected error inserting into SQL")


async def remove_unique_constraint(session: AsyncSession, table_name: str, column_name: str) -> None:
    """Remove UNIQUE constraint from a specific column."""
    find_constraint_sql = text("""
        SELECT tc.constraint_name
        FROM information_schema.table_constraints AS tc
        JOIN information_schema.constraint_column_usage AS ccu
          ON tc.constraint_name = ccu.constraint_name
        WHERE constraint_type = 'UNIQUE'
          AND tc.table_name = :table_name
          AND ccu.column_name = :column_name
    """)

    result = await session.execute(find_constraint_sql, {"table_name": table_name, "column_name": column_name})
    rows = result.fetchall()

    for row in rows:
        constraint_name = row[0]
        logger.info("Dropping unique constraint %s on %s.%s", constraint_name, table_name, column_name)
        drop_sql = text('ALTER TABLE "' + table_name + '" DROP CONSTRAINT "' + constraint_name + '"')
        await session.execute(drop_sql)

    await session.commit()


class _IncrementalMigrationContext:
    """Context for incremental migration to reduce function arguments."""

    def __init__(
        self,
        session_id: str,
        table_name: str,
        sql_session: AsyncSession,
    ) -> None:
        self.session_id = session_id
        self.table_name = table_name
        self.sql_session = sql_session


async def _process_document_incremental(
    doc: dict[str, Any],
    analysis: dict[str, Any],
    ctx: _IncrementalMigrationContext,
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    """Process document for incremental migration with type drift detection.

    Returns:
        Tuple of (sql_row, overflow, updated_analysis)

    """
    username = doc.get("username", "unknown")
    sys_ingested_at = doc.get("sys_ingested_at")
    t_stamp = doc.get("t_stamp")

    sql_row = {"session_id": ctx.session_id, "username": username}
    overflow = {}

    if sys_ingested_at is not None:
        sql_row["sys_ingested_at"] = sys_ingested_at
    if t_stamp is not None:
        sql_row["t_stamp"] = t_stamp

    for key, value in doc.items():
        if key in ["_id", "session_id", "username", "sys_ingested_at", "t_stamp"]:
            continue

        meta = analysis.get(key)
        target_overflow = True

        if meta and meta["target"] == "sql":
            try:
                casted_val = cast_value(value, meta["type"])
                sql_row[key] = casted_val
                target_overflow = False
            except (ValueError, TypeError):
                # Type drift detected — migrate column to JSONB overflow
                logger.warning(
                    "Type drift detected for column '%s': cannot cast value to %s",
                    key,
                    meta["type"],
                )
                logger.info("Triggering column migration: '%s' from SQL to JSONB overflow", key)

                await migrate_column_to_jsonb(
                    session_id=ctx.session_id,
                    column_name=key,
                    table_name=ctx.table_name,
                    sql_session=ctx.sql_session,
                )

                # Reload updated schema
                schema_reload_query = text("SELECT schema_json FROM session_metadata WHERE session_id = :sid")
                schema_reload_result = await ctx.sql_session.execute(schema_reload_query, {"sid": ctx.session_id})
                schema_reload_row = schema_reload_result.fetchone()
                if schema_reload_row and schema_reload_row[0]:
                    analysis = json.loads(schema_reload_row[0])

                target_overflow = True

        if target_overflow:
            overflow[key] = value

    return sql_row, overflow, analysis


async def migrate_column_to_jsonb(
    session_id: str,
    column_name: str,
    table_name: str,
    sql_session: AsyncSession,
) -> int:
    """Migrate a column from SQL to JSONB overflow due to type drift.

    Steps:
    1. Reads all values for the column from SQL (for this session)
    2. Merges those values into the overflow_data JSONB column
    3. Marks the column for 'mongo' (meaning JSONB overflow) in the cached schema

    Args:
        session_id: Session identifier
        column_name: Name of the column to migrate
        table_name: SQL table name
        sql_session: SQL session

    Returns:
        Number of records updated

    """
    logger.info("Migrating column '%s' from SQL to JSONB overflow for session %s", column_name, session_id)

    # 1. Fetch existing data for this column
    query = text('SELECT "sys_ingested_at", "' + column_name + '" FROM "' + table_name + '" WHERE session_id = :sid')
    result = await sql_session.execute(query, {"sid": session_id})
    rows = result.fetchall()

    if not rows:
        logger.warning("No rows found for session %s in SQL", session_id)
        return 0

    # 2. Merge column values into overflow_data JSONB
    updated_count = 0
    for row in rows:
        sys_ingested_at_val = row[0]
        column_val = row[1]

        # Build a JSON patch with the column value
        patch = json.dumps({column_name: column_val})
        update_sql = text(
            'UPDATE "' + table_name + '" SET overflow_data = COALESCE(overflow_data, \'{}\'::jsonb) || :patch::jsonb '
            "WHERE session_id = :sid AND sys_ingested_at = :ts"
        )
        await sql_session.execute(update_sql, {"patch": patch, "sid": session_id, "ts": sys_ingested_at_val})
        updated_count += 1

    # 3. Update cached schema to mark as 'mongo' (JSONB overflow)
    schema_query = text("SELECT schema_json FROM session_metadata WHERE session_id = :sid")
    schema_result = await sql_session.execute(schema_query, {"sid": session_id})
    schema_row = schema_result.fetchone()

    if schema_row and schema_row[0]:
        schema = json.loads(schema_row[0])
        if column_name in schema:
            schema[column_name]["target"] = "mongo"
            logger.info("Updated schema: %s target changed to JSONB overflow", column_name)
            updated_schema_json = json.dumps(schema)
            await sql_session.execute(
                text("UPDATE session_metadata SET schema_json = :schema WHERE session_id = :sid"),
                {"sid": session_id, "schema": updated_schema_json},
            )
            await sql_session.commit()

    logger.info("Successfully migrated %d values of column '%s' to JSONB overflow", updated_count, column_name)
    return updated_count


@session
async def migrate_data(
    session_id: str,
    analysis: dict[str, Any],
    sql_session: AsyncSession,
) -> None:
    """Migrate data from staging to permanent storage based on analysis.

    Uses single SQL table 'chiral_data' with overflow_data JSONB column.
    """
    table_name = "chiral_data"

    # Get existing columns
    existing_cols_sql = text("SELECT column_name FROM information_schema.columns WHERE table_name = :table_name")
    result = await sql_session.execute(existing_cols_sql, {"table_name": table_name})
    existing_columns = [row[0] for row in result.fetchall()]

    # Setup system columns and get valid SQL columns
    sys_cols_to_add, valid_sql_cols = _ensure_system_columns(existing_columns)
    schema_cols_to_add = _build_schema_columns(analysis, existing_columns, valid_sql_cols)

    columns_to_add = sys_cols_to_add + schema_cols_to_add

    # Apply schema changes
    if columns_to_add:
        alter_stmt = f'ALTER TABLE "{table_name}" {", ".join(columns_to_add)};'
        try:
            await sql_session.execute(text(alter_stmt))
            await sql_session.commit()
        except SQLAlchemyError:
            logger.exception("Schema Evolution Failed")
            return

    # Read staging documents from PostgreSQL staging_data table
    staging_result = await sql_session.execute(
        text("SELECT id, data FROM staging_data WHERE session_id = :sid"),
        {"sid": session_id},
    )
    staging_rows = staging_result.fetchall()

    processed_ids = []
    for row in staging_rows:
        staging_id = row[0]
        raw_data = row[1]

        doc = json.loads(raw_data) if isinstance(raw_data, str) else raw_data

        sql_row, overflow = _process_document(doc, session_id, analysis)

        # Insert into chiral_data with overflow_data JSONB
        await _insert_sql_row(sql_row, overflow, valid_sql_cols, table_name, sql_session)

        processed_ids.append(staging_id)

    # Cleanup staging
    if processed_ids:
        placeholders = ", ".join([f":id_{i}" for i in range(len(processed_ids))])
        delete_sql = text(f"DELETE FROM staging_data WHERE id IN ({placeholders})")
        params = {f"id_{i}": pid for i, pid in enumerate(processed_ids)}
        await sql_session.execute(delete_sql, params)

    schema_json = json.dumps(analysis)
    await sql_session.execute(
        text("UPDATE session_metadata SET status = 'migrated', schema_json = :schema WHERE session_id = :sid"),
        {"sid": session_id, "schema": schema_json},
    )
    await sql_session.commit()


@session
async def migrate_incremental(
    session_id: str,
    sql_session: AsyncSession,
) -> int:
    """Migrate new data from staging for a session that has already been analyzed.

    Uses the cached schema from session_metadata.

    Args:
        session_id: Session identifier
        sql_session: SQL session (injected)

    Returns:
        Number of records migrated

    """
    # Fetch cached schema
    schema_query = text("SELECT schema_json FROM session_metadata WHERE session_id = :sid")
    result = await sql_session.execute(schema_query, {"sid": session_id})
    row = result.fetchone()

    if not row or not row[0]:
        logger.warning("No schema found for session %s, cannot perform incremental migration", session_id)
        return 0

    analysis = json.loads(row[0])

    # Get staging documents from PostgreSQL
    staging_result = await sql_session.execute(
        text("SELECT id, data FROM staging_data WHERE session_id = :sid"),
        {"sid": session_id},
    )
    staging_rows = staging_result.fetchall()

    if not staging_rows:
        return 0

    table_name = "chiral_data"
    migrated_count = 0

    # Build valid SQL columns list
    valid_sql_cols = ["session_id", "username", "sys_ingested_at", "t_stamp"]
    for col, meta in analysis.items():
        if meta["target"] == "sql" and col not in valid_sql_cols:
            valid_sql_cols.append(col)

    ctx = _IncrementalMigrationContext(session_id, table_name, sql_session)

    processed_ids = []
    for row in staging_rows:
        staging_id = row[0]
        raw_data = row[1]

        doc = json.loads(raw_data) if isinstance(raw_data, str) else raw_data

        sql_row, overflow, analysis = await _process_document_incremental(doc, analysis, ctx)

        # Rebuild valid_sql_cols if schema changed
        valid_sql_cols = ["session_id", "username", "sys_ingested_at", "t_stamp"]
        for col, meta in analysis.items():
            if meta["target"] == "sql" and col not in valid_sql_cols:
                valid_sql_cols.append(col)

        # Insert into chiral_data with overflow JSONB
        await _insert_sql_row(sql_row, overflow, valid_sql_cols, table_name, sql_session)

        migrated_count += 1
        processed_ids.append(staging_id)

    # Cleanup staging
    if processed_ids:
        placeholders = ", ".join([f":id_{i}" for i in range(len(processed_ids))])
        delete_sql = text(f"DELETE FROM staging_data WHERE id IN ({placeholders})")
        params = {f"id_{i}": pid for i, pid in enumerate(processed_ids)}
        await sql_session.execute(delete_sql, params)

    await sql_session.execute(
        text("UPDATE session_metadata SET status = 'migrated' WHERE session_id = :sid"),
        {"sid": session_id},
    )
    await sql_session.commit()

    logger.info("Incrementally migrated %d records for session %s", migrated_count, session_id)
    return migrated_count
