# Copyright (c) 2026 Chiral Contributors
#
# This source code is licensed under the MIT license found in the
# LICENSE file in the root directory of this source tree.

"""Main Application Entry Point."""

import sys
from pathlib import Path
from typing import Any

# Add the parent directory (src) to sys.path to allow imports from 'chiral' package
sys.path.append(str(Path(__file__).parent.parent.parent))

from fastapi import BackgroundTasks, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from chiral.core.ingestion import ingest_data
from chiral.core.orchestrator import flush_staging, trigger_worker
from chiral.core.query_service import (
    CreateExecutionValidationError,
    execute_json_request,
    translate_json_request_with_metadata,
)
from chiral.db.sessions import session

app = FastAPI(title="Chiral DB Assignment")

app.add_middleware(
    CORSMiddleware,  # type: ignore[arg-type]
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class IngestRequest(BaseModel):
    """Request model for data ingestion endpoint."""

    data: dict[str, Any]


class QueryTranslateRequest(BaseModel):
    """Request model for query translation endpoint."""

    operation: str
    table: str = "chiral_data"
    session_id: str | None = None
    select: list[str] | None = None
    filters: list[dict[str, Any]] | None = None
    payload: dict[str, Any] | None = None
    updates: dict[str, Any] | None = None
    limit: int | None = None
    offset: int | None = None
    decomposition_plan: dict[str, Any] | None = None
    analysis_metadata: dict[str, Any] | None = None


@app.post("/flush/{session_id}")
async def flush_endpoint(session_id: str) -> dict[str, int]:
    """Endpoint to force flush staging data."""
    return await flush_staging(session_id)


@app.post("/ingest")
async def ingest_endpoint(request: IngestRequest, background_tasks: BackgroundTasks) -> dict[str, Any]:
    """Endpoint to ingest data."""
    result = await ingest_data(data=request.data, session_id=request.data["session_id"])

    if result.get("worker_triggered"):
        incremental = result.get("incremental", False)
        background_tasks.add_task(trigger_worker, request.data["session_id"], incremental=incremental)

    return result


@app.get("/")
def root() -> dict[str, str]:
    """Root endpoint returning API status."""
    return {"message": "Chiral DB Assignment API is running."}


@app.post("/query/translate")
async def translate_query_endpoint(request: QueryTranslateRequest) -> dict[str, Any]:
    """Translate JSON CRUD request into SQL/JSONB query and bind params."""
    built_query = await translate_json_request_with_metadata(request.model_dump(exclude_none=True))
    return {
        "sql": built_query.sql,
        "params": built_query.params,
    }


@app.post("/query/execute")
async def execute_query_endpoint(request: QueryTranslateRequest) -> dict[str, Any]:
    """Translate and execute JSON CRUD request.

    - read: returns rows + row_count
    - update/delete: returns affected_rows
    - create: returns mode-aware contract (migrated_sync or queued_async)
    """
    try:
        return await execute_json_request(request.model_dump(exclude_none=True))
    except CreateExecutionValidationError as exc:
        raise HTTPException(
            status_code=400,
            detail={
                "mode": "failed_validation",
                "error": str(exc),
            },
        ) from exc


@app.get("/schema/metadata")
async def schema_metadata_endpoint() -> dict[str, Any]:
    """Dynamically reflects the live PostgreSQL database schema."""

    @session
    async def _fetch(sql_session: AsyncSession) -> dict[str, Any]:
        schema = {}

        # Query all public tables manually to avoid run_sync deadlocks
        result = await sql_session.execute(
            text(
                "SELECT table_name FROM information_schema.tables WHERE table_schema = 'public' AND table_type = 'BASE TABLE'"
            )
        )
        valid_tables = [row[0] for row in result.fetchall()]

        for t in valid_tables:
            cols_result = await sql_session.execute(
                text("SELECT column_name, data_type FROM information_schema.columns WHERE table_name = :t"), {"t": t}
            )
            cols = [{"name": row[0], "type": row[1]} for row in cols_result.fetchall()]

            # Fetch 3 preview rows to populate the schema node hover views dynamically!
            try:
                sample_result = await sql_session.execute(text(f"SELECT * FROM {t} LIMIT 3"))
                # JSON serialize simple types for UI compatibility
                sample_data = []
                for row in sample_result.fetchall():
                    row_dict = {}
                    for i, key in enumerate(sample_result.keys()):
                        val = row[i]
                        if isinstance(val, (dict, list, str, int, float, bool)) or val is None:
                            row_dict[key] = val
                        else:
                            row_dict[key] = str(val)
                    sample_data.append(row_dict)
            except Exception:
                sample_data = []

            schema[t] = {
                "columns": cols,
                "primary_keys": ["id" if t != "session_metadata" else "session_id"],
                "foreign_keys": [],
                "sampleData": sample_data,
            }
        return schema

    return await _fetch()
