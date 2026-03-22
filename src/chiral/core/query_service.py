# Copyright (c) 2026 Chiral Contributors
#
# This source code is licensed under the MIT license found in the
# LICENSE file in the root directory of this source tree.

"""JSON request to SQL/JSONB query translation service."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any

from sqlalchemy import text

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

from chiral.db.query_builder import BuiltQuery, CrudQueryBuilder, InferredJoin
from chiral.db.sessions import session
from chiral.domain.key_policy import build_dynamic_child_key_spec


def _extract_decomposition_plan(request: dict[str, Any]) -> dict[str, Any]:
    direct_plan = request.get("decomposition_plan")
    if isinstance(direct_plan, dict):
        return direct_plan

    metadata = request.get("analysis_metadata")
    if isinstance(metadata, dict):
        nested = metadata.get("decomposition_plan")
        if isinstance(nested, dict):
            return nested

    return {"version": 1, "parent_table": "chiral_data", "entities": []}


def _extract_session_id(request: dict[str, Any]) -> str | None:
    direct = request.get("session_id")
    if isinstance(direct, str) and direct:
        return direct

    payload = request.get("payload")
    if isinstance(payload, dict):
        payload_session_id = payload.get("session_id")
        if isinstance(payload_session_id, str) and payload_session_id:
            return payload_session_id

    updates = request.get("updates")
    if isinstance(updates, dict):
        updates_session_id = updates.get("session_id")
        if isinstance(updates_session_id, str) and updates_session_id:
            return updates_session_id

    filters = request.get("filters", [])
    if isinstance(filters, list):
        for item in filters:
            if not isinstance(item, dict):
                continue
            if str(item.get("field", "")).lower() != "session_id":
                continue
            value = item.get("value")
            if isinstance(value, str) and value:
                return value

    return None


async def _load_decomposition_plan_from_metadata(sql_session: AsyncSession, session_id: str) -> dict[str, Any]:
    result = await sql_session.execute(
        text("SELECT schema_json FROM session_metadata WHERE session_id = :sid"),
        {"sid": session_id},
    )
    row = result.fetchone()
    if not row:
        return {"version": 1, "parent_table": "chiral_data", "entities": []}

    raw_schema = row[0]
    if isinstance(raw_schema, str):
        try:
            schema = json.loads(raw_schema)
        except json.JSONDecodeError:
            schema = {}
    elif isinstance(raw_schema, dict):
        schema = raw_schema
    else:
        schema = {}

    if not isinstance(schema, dict):
        return {"version": 1, "parent_table": "chiral_data", "entities": []}

    metadata = schema.get("__analysis_metadata__", {})
    if not isinstance(metadata, dict):
        return {"version": 1, "parent_table": "chiral_data", "entities": []}

    decomposition_plan = metadata.get("decomposition_plan", {})
    if not isinstance(decomposition_plan, dict):
        return {"version": 1, "parent_table": "chiral_data", "entities": []}

    entities = decomposition_plan.get("entities", [])
    if not isinstance(entities, list):
        entities = []

    return {
        "version": int(decomposition_plan.get("version", 1) or 1),
        "parent_table": str(decomposition_plan.get("parent_table", "chiral_data")),
        "entities": entities,
    }


async def _hydrate_request_with_decomposition_plan(
    request: dict[str, Any],
    sql_session: AsyncSession,
) -> dict[str, Any]:
    existing_plan = _extract_decomposition_plan(request)
    existing_entities = existing_plan.get("entities", [])
    if isinstance(existing_entities, list) and existing_entities:
        return request

    session_id = _extract_session_id(request)
    if not session_id:
        return request

    metadata_plan = await _load_decomposition_plan_from_metadata(sql_session, session_id)
    entities = metadata_plan.get("entities", [])
    if not isinstance(entities, list) or not entities:
        return request

    hydrated = dict(request)
    hydrated["decomposition_plan"] = metadata_plan
    return hydrated


def _build_inferred_joins_for_request(request: dict[str, Any], table_name: str) -> list[InferredJoin]:
    plan = _extract_decomposition_plan(request)
    entities = plan.get("entities", [])
    if not isinstance(entities, list) or not entities:
        return []

    referenced_prefixes: set[str] = set()
    select_fields = request.get("select", ["*"])
    filters = request.get("filters", [])

    if isinstance(select_fields, list):
        for field in select_fields:
            if isinstance(field, str) and "." in field:
                prefix = field.split(".", 1)[0]
                if prefix != "overflow_data":
                    referenced_prefixes.add(prefix)

    if isinstance(filters, list):
        for item in filters:
            if not isinstance(item, dict):
                continue
            field = item.get("field")
            if isinstance(field, str) and "." in field:
                prefix = field.split(".", 1)[0]
                if prefix != "overflow_data":
                    referenced_prefixes.add(prefix)

    inferred: list[InferredJoin] = []
    for entity in entities:
        if not isinstance(entity, dict):
            continue

        source_field = entity.get("source_field")
        child_table = entity.get("child_table")
        if not isinstance(source_field, str) or not isinstance(child_table, str):
            continue
        if source_field not in referenced_prefixes:
            continue

        raw_child_column_types = entity.get("child_column_types", {})
        child_column_types = {
            str(column): str(inferred_type)
            for column, inferred_type in raw_child_column_types.items()
            if isinstance(column, str) and isinstance(inferred_type, str)
        }

        key_spec = build_dynamic_child_key_spec(parent_table=table_name, source_field=source_field)
        parent_fk_column = key_spec.foreign_keys[0]["local_column"]
        inferred.append(
            InferredJoin(
                source_field=source_field,
                child_table=child_table,
                parent_fk_column=parent_fk_column,
                child_column_types=child_column_types,
            )
        )

    return inferred


def translate_json_request(request: dict[str, Any]) -> BuiltQuery:
    """Translate a user JSON CRUD request into a parameterized SQL query.

    Supported operation values: read, create, update, delete.
    """
    operation = str(request.get("operation", "")).lower()
    table_name = str(request.get("table", "chiral_data"))
    inferred_joins = _build_inferred_joins_for_request(request, table_name)
    builder = CrudQueryBuilder(table_name=table_name, inferred_joins=inferred_joins)

    if operation == "read":
        return builder.build_select(
            select_fields=request.get("select", ["*"]),
            filters=request.get("filters", []),
            limit=request.get("limit"),
            offset=request.get("offset"),
        )

    if operation == "create":
        payload = request.get("payload", {})
        if not isinstance(payload, dict):
            msg = "create operation requires object payload"
            raise ValueError(msg)
        return builder.build_insert(payload)

    if operation == "update":
        updates = request.get("updates", {})
        if not isinstance(updates, dict):
            msg = "update operation requires object updates"
            raise ValueError(msg)
        return builder.build_update(updates=updates, filters=request.get("filters", []))

    if operation == "delete":
        return builder.build_delete(filters=request.get("filters", []))

    msg = f"Unsupported operation: {operation}"
    raise ValueError(msg)


@session
async def translate_json_request_with_metadata(
    request: dict[str, Any],
    sql_session: AsyncSession,
) -> BuiltQuery:
    """Translate JSON request, auto-hydrating decomposition plan from session metadata when absent."""
    hydrated_request = await _hydrate_request_with_decomposition_plan(request, sql_session)
    return translate_json_request(hydrated_request)


@session
async def execute_json_request(
    request: dict[str, Any],
    sql_session: AsyncSession,
) -> dict[str, Any]:
    """Translate and execute a JSON CRUD request against SQL storage."""
    return await _execute_json_request_impl(request=request, sql_session=sql_session)


async def _execute_json_request_impl(
    request: dict[str, Any],
    sql_session: AsyncSession,
) -> dict[str, Any]:
    """Execute translated requests (testable without session decorator)."""
    operation = str(request.get("operation", "")).lower()
    hydrated_request = await _hydrate_request_with_decomposition_plan(request, sql_session)
    built = translate_json_request(hydrated_request)

    result = await sql_session.execute(text(built.sql), built.params)

    if operation == "read":
        rows = [dict(row) for row in result.mappings().all()]
        return {
            "sql": built.sql,
            "params": built.params,
            "rows": rows,
            "row_count": len(rows),
        }

    affected_rows = int(getattr(result, "rowcount", 0) or 0)
    return {
        "sql": built.sql,
        "params": built.params,
        "affected_rows": affected_rows,
    }
