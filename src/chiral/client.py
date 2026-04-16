# Copyright (c) 2026 Chiral Contributors
#
# This source code is licensed under the MIT license found in the
# LICENSE file in the root directory of this source tree.

"""Core entry point for the ChiralDB framework."""

import asyncio
import json
import logging
import types
from typing import Any, Self

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine, async_sessionmaker, create_async_engine

from chiral.core.ingestion import ingest_data
from chiral.core.orchestrator import flush_staging, trigger_worker
from chiral.core.query_service import execute_json_request, translate_json_request_with_metadata
from chiral.db.schema import init_metadata_table

logger = logging.getLogger(__name__)

class ChiralClient:
    """Core client for managing the ChiralDB framework."""

    def __init__(self, database_url: str, **engine_kwargs: Any) -> None:
        """Initialize the ChiralClient."""
        self.database_url = database_url
        self.engine: AsyncEngine = create_async_engine(self.database_url, **engine_kwargs)
        self.session_factory = async_sessionmaker(bind=self.engine, expire_on_commit=False)
        self._background_tasks: set[asyncio.Task[Any]] = set()

    async def connect(self) -> None:
        """Initialize connection and materialize base system schemas."""
        async with self.session_factory() as session:
            await init_metadata_table(session)
            await session.commit()

    async def disconnect(self) -> None:
        """Close connections and gracefully wait for background migration tasks."""
        if self._background_tasks:
            logger.info("Waiting for %d background migration tasks to complete...", len(self._background_tasks))
            await asyncio.gather(*self._background_tasks, return_exceptions=True)
        await self.engine.dispose()

    async def __aenter__(self) -> Self:
        """Enter async context manager."""
        await self.connect()
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: types.TracebackType | None,
    ) -> None:
        """Exit async context manager."""
        await self.disconnect()

    async def ingest(self, session_id: str, data: dict[str, Any]) -> dict[str, Any]:
        """Ingest a record autonomously and trigger background migrations if needed."""
        async with self.session_factory() as session:
            result = await ingest_data(data=data, session_id=session_id, sql_session=session)
            await session.commit()

        if result.get("worker_triggered"):
            incremental = bool(result.get("incremental", False))
            task = asyncio.create_task(trigger_worker(session_id, incremental=incremental, engine=self.engine))
            self._background_tasks.add(task)
            task.add_done_callback(self._background_tasks.discard)

        return result

    async def query(self, request: dict[str, Any]) -> dict[str, Any]:
        """Translate and execute a logical JSON query."""
        async with self.session_factory() as session:
            result = await execute_json_request(request=request, sql_session=session)
            await session.commit()

        if result.get("mode") == "queued_async" and result.get("worker_triggered"):
            incremental = bool(result.get("incremental", False))
            session_id = request.get("session_id")
            if not session_id and isinstance(request.get("payload"), dict):
                session_id = request["payload"].get("session_id")

            if session_id:
                task = asyncio.create_task(trigger_worker(session_id, incremental=incremental, engine=self.engine))
                self._background_tasks.add(task)
                task.add_done_callback(self._background_tasks.discard)

        return result

    async def flush(self, session_id: str) -> dict[str, int]:
        """Force flush staging data to main tables."""
        return await flush_staging(session_id, engine=self.engine)

    async def translate_only(self, request: dict[str, Any]) -> dict[str, Any]:
        """Translate a JSON request to SQL without executing it (for dry-runs)."""
        async with self.session_factory() as session:
            built_query = await translate_json_request_with_metadata(request, sql_session=session)
            return {"sql": built_query.sql, "params": built_query.params}

    async def get_logical_schema(self, session_id: str) -> list[str]:
        """Retrieve the logical schema (field names) for a given session."""
        async with self.session_factory() as session:
            result = await session.execute(
                text("SELECT schema_json FROM session_metadata WHERE session_id = :sid"), {"sid": session_id}
            )
            row = result.fetchone()
            if not row or not row[0]:
                return ["session_id", "sys_ingested_at", "t_stamp", "username"]

            schema_json = json.loads(row[0]) if isinstance(row[0], str) else row[0]
            fields = ["session_id", "sys_ingested_at", "t_stamp", "username"]

            for key, meta in schema_json.items():
                if key == "__analysis_metadata__":
                    plan = meta.get("decomposition_plan", {})
                    for entity in plan.get("entities", []):
                        source = entity.get("source_field")
                        if source and source not in fields:
                            fields.append(source)
                        fields.extend(f"{source}.{child_col}" for child_col in entity.get("child_columns", []))
                    continue
                if key not in fields:
                    fields.append(key)

            return sorted(fields)

    async def get_active_sessions(self) -> list[str]:
        """Retrieve a list of active session IDs."""
        async with self.session_factory() as session:
            result = await session.execute(text("SELECT session_id FROM session_metadata ORDER BY created_at DESC"))
            return [row[0] for row in result.fetchall()]
