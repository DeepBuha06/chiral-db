# Copyright (c) 2026 Chiral Contributors
#
# This source code is licensed under the MIT license found in the
# LICENSE file in the root directory of this source tree.

"""System-level ACID tests through Chiral service entry points."""

from __future__ import annotations

import asyncio
import time
from typing import TYPE_CHECKING
from unittest.mock import patch

import pytest
from sqlalchemy import text

from chiral.core.ingestion import ingest_data
from chiral.core.query_service import CreateExecutionValidationError, execute_json_request

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncEngine

pytestmark = pytest.mark.asyncio


class TestAcidProperties:
    """Validate ACID properties through Chiral system APIs."""

    @staticmethod
    async def _fetch_scalar(engine: AsyncEngine, query: str, params: dict[str, object]) -> int:
        async with engine.connect() as conn:
            result = await conn.execute(text(query), params)
            raw = result.scalar_one_or_none()
        return int(raw) if raw is not None else 0

    async def test_atomicity_ingest_rolls_back_staging_and_count_on_failure(self, acid_engine: AsyncEngine) -> None:
        """If ingest fails mid-flight, system should not leave partial staging/count writes."""
        session_id = "acid_system_atomicity"
        record = {"username": "atomic_user", "temperature": 30, "t_stamp": time.time()}

        with (
            patch("chiral.core.ingestion.MonotonicClock.get_sys_ingested_at", side_effect=RuntimeError("boom")),
            pytest.raises(RuntimeError, match="boom"),
        ):
            await ingest_data(data=record, session_id=session_id)

        staging_count = await self._fetch_scalar(
            acid_engine,
            "SELECT COUNT(*) FROM staging_data WHERE session_id = :sid",
            {"sid": session_id},
        )
        metadata_count = await self._fetch_scalar(
            acid_engine,
            "SELECT COUNT(*) FROM session_metadata WHERE session_id = :sid",
            {"sid": session_id},
        )
        record_count = await self._fetch_scalar(
            acid_engine,
            "SELECT COALESCE(MAX(record_count), 0) FROM session_metadata WHERE session_id = :sid",
            {"sid": session_id},
        )

        # Session row may be initialized first, but the ingest unit must not partially apply data.
        assert staging_count == 0
        assert metadata_count == 1
        assert record_count == 0

    async def test_consistency_create_requires_session_id_and_preserves_state(self, acid_engine: AsyncEngine) -> None:
        """System request validation should reject inconsistent create payloads without side effects."""
        bad_request = {
            "operation": "create",
            "table": "chiral_data",
            "payload": {
                "username": "missing_session",
                "sys_ingested_at": 1.0,
                "t_stamp": 1.0,
                "overflow_data": "{}",
            },
        }

        with pytest.raises(CreateExecutionValidationError, match="requires session_id"):
            await execute_json_request(bad_request)

        rows = await self._fetch_scalar(
            acid_engine,
            "SELECT COUNT(*) FROM chiral_data",
            {},
        )
        staging = await self._fetch_scalar(
            acid_engine,
            "SELECT COUNT(*) FROM staging_data",
            {},
        )
        assert rows == 0
        assert staging == 0

    async def test_isolation_concurrent_ingest_has_no_lost_updates(self, acid_engine: AsyncEngine) -> None:
        """Concurrent system ingests must serialize counter updates correctly."""
        session_id = "acid_system_isolation"
        total_writes = 4

        # Prime the session once to avoid concurrent init contention and then test steady-state isolation.
        await ingest_data(
            data={"username": "iso_prime", "temperature": -1, "t_stamp": time.time()},
            session_id=session_id,
        )

        async def one_ingest(idx: int) -> dict[str, object]:
            payload = {
                "username": f"iso_user_{idx}",
                "temperature": idx,
                "t_stamp": time.time() + idx,
            }
            attempts = 0
            while True:
                attempts += 1
                try:
                    return await ingest_data(data=payload, session_id=session_id)
                except Exception as exc:
                    if "deadlock detected" not in str(exc).lower() or attempts >= 8:
                        raise
                    await asyncio.sleep(0.03 * attempts)

        results = await asyncio.gather(*(one_ingest(i) for i in range(total_writes)))

        final_count = await self._fetch_scalar(
            acid_engine,
            "SELECT record_count FROM session_metadata WHERE session_id = :sid",
            {"sid": session_id},
        )
        staging_count = await self._fetch_scalar(
            acid_engine,
            "SELECT COUNT(*) FROM staging_data WHERE session_id = :sid",
            {"sid": session_id},
        )

        assert len(results) == total_writes
        assert final_count == total_writes + 1
        assert staging_count == total_writes + 1

    async def test_durability_create_visible_on_fresh_session(self, acid_engine: AsyncEngine) -> None:
        """Committed create through system API must persist and be readable from fresh DB sessions."""
        session_id = "acid_system_durability"
        create_request = {
            "operation": "create",
            "table": "chiral_data",
            "payload": {
                "session_id": session_id,
                "username": "durable_user",
                "sys_ingested_at": 123.45,
                "t_stamp": 123.45,
                "overflow_data": "{}",
            },
        }

        response = await execute_json_request(create_request)
        assert int(response.get("affected_rows", 0)) == 1

        async with acid_engine.connect() as conn:
            result = await conn.execute(
                text("SELECT COUNT(*) FROM chiral_data WHERE session_id = :sid AND username = :username"),
                {"sid": session_id, "username": "durable_user"},
            )
            first_read = int(result.scalar_one())

        async with acid_engine.connect() as conn:
            result = await conn.execute(
                text("SELECT COUNT(*) FROM chiral_data WHERE session_id = :sid AND username = :username"),
                {"sid": session_id, "username": "durable_user"},
            )
            second_read = int(result.scalar_one())

        assert first_read == 1
        assert second_read == 1
