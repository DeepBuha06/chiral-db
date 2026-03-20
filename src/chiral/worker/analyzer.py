# Copyright (c) 2026 Chiral Contributors
#
# This source code is licensed under the MIT license found in the
# LICENSE file in the root directory of this source tree.

"""Worker Analysis Logic."""

import json
from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from chiral.db.sessions import session
from chiral.utils.heuristics import calculate_entropy


@session
async def analyze_staging(
    sql_session: AsyncSession,
) -> dict[str, Any]:
    """Analyze the first 100 documents in the staging table to determine the schema.

    Args:
        sql_session: Injected SQL session.

    Returns:
        Dictionary containing column metadata and placement decisions.

    """
    # Fetch 100 documents from staging_data (JSONB) — replaces MongoDB staging collection
    result = await sql_session.execute(text("SELECT data FROM staging_data LIMIT 100"))
    rows = result.fetchall()

    if not rows:
        return {}

    # Parse JSONB data — asyncpg returns dicts directly, but handle str just in case
    docs = []
    for row in rows:
        raw = row[0]
        if isinstance(raw, str):
            docs.append(json.loads(raw))
        else:
            docs.append(raw)

    # 2. Pivot data to organize by column (attribute)
    columns: dict[str, list[Any]] = {}

    for doc in docs:
        for key, value in doc.items():
            if key not in columns:
                columns[key] = []
            columns[key].append(value)

    total_docs = len(docs)
    analysis_result = {}

    for col_name, values in columns.items():
        # Skip system columns
        if col_name in ["sys_ingested_at", "t_stamp", "username"]:
            continue

        # Uniqueness Check
        try:
            is_unique = len(set(values)) == len(values) and len(values) == total_docs
        except TypeError:
            is_unique = False

        # Entropy Calculation
        entropy = calculate_entropy(values)

        # Type Inference
        inferred_type = infer_type(values)

        # Placement Decision
        if inferred_type in {"dict", "list"}:
            target = "mongo"  # Nested structures → JSONB overflow (kept as "mongo" label for schema compat)
        elif entropy > 0:
            target = "mongo"  # Type drift → JSONB overflow
        else:
            target = "sql"  # Stable type → SQL column

        analysis_result[col_name] = {
            "unique": is_unique,
            "entropy": entropy,
            "target": target,
            "type": inferred_type,
        }

    return analysis_result


def infer_type(values: list[Any]) -> str:
    """Infer the dominant Python type from a list of values."""
    if not values:
        return "str"

    valid_values = [v for v in values if v is not None]
    if not valid_values:
        return "str"

    first_type = type(valid_values[0])
    if any(type(x) is not first_type for x in valid_values):
        return "str"

    first_value = valid_values[0]
    type_map = {
        bool: "bool",
        int: "int",
        float: "float",
        dict: "dict",
        list: "list",
    }
    for type_cls, type_name in type_map.items():
        if isinstance(first_value, type_cls):
            return type_name
    return "str"
