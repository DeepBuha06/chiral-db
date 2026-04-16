# Copyright (c) 2026 Chiral Contributors
#
# This source code is licensed under the MIT license found in the
# LICENSE file in the root directory of this source tree.

"""Simulation script to feed complex nested data into the Chiral API."""

import asyncio
import logging
import random
from datetime import UTC, datetime
from typing import Any

import httpx

CHIRAL_API_URL = "http://127.0.0.1:8000/ingest"
SESSION_ID = "simulation_test_02"  # Using a fresh session!
TOTAL_RECORDS = 1000

logging.basicConfig(level=logging.INFO, format="%(message)s")
logging.getLogger("httpx").setLevel(logging.WARNING)
logger = logging.getLogger(__name__)

def _build_comment(comment_id: int) -> dict[str, object]:
    return {
        "comment_id": comment_id,
        "text": f"comment-{comment_id}",
        "score": round(random.uniform(0.0, 1.0), 3),
        "is_flagged": random.choice([True, False]),
        "meta": {"sentiment": random.choice(["positive", "neutral", "negative"])},
    }

def _build_event(event_id: int) -> dict[str, object]:
    return {
        "event_id": event_id,
        "event_type": random.choice(["view", "click", "purchase"]),
        "amount": round(random.uniform(5, 500), 2),
    }

def generate_complex_record(index: int) -> dict[str, Any]:
    """Generate a highly nested synthetic record."""
    comment_count = random.randint(1, 4)
    event_count = random.randint(1, 3)

    return {
        "session_id": SESSION_ID,
        "username": f"user_{index % 50}",
        "t_stamp": datetime.now(tz=UTC).timestamp(),
        "city": random.choice(["Paris", "Berlin", "Tokyo", "Delhi"]),
        "temperature": random.randint(15, 40),
        "device": random.choice(["android", "ios", "web"]),
        "metadata": {
            "source": "simulation",
            "version": "2.0",
        },
        # These homogeneous arrays will be beautifully decomposed into SQL tables!
        "comments": [_build_comment(index * 10 + offset) for offset in range(comment_count)],
        "events": [_build_event(index * 10 + offset) for offset in range(event_count)],
    }

async def feed_data() -> None:
    """Stream synthetic records to the Chiral API."""
    async with httpx.AsyncClient(timeout=30.0) as client:
        logger.info("Streaming %d complex records to %s...", TOTAL_RECORDS, CHIRAL_API_URL)
        for i in range(TOTAL_RECORDS):
            payload = {"data": generate_complex_record(i)}
            res = await client.post(CHIRAL_API_URL, json=payload)
            if res.status_code == 200 and i > 0 and i % 100 == 0:
                logger.info("Ingested %d records...", i)

        logger.info("Ingestion complete. Sending Flush signal to force schema finalization...")
        await client.post(f"http://127.0.0.1:8000/flush/{SESSION_ID}")
        logger.info("Flush complete. Schema is now finalized!")

if __name__ == "__main__":
    asyncio.run(feed_data())
