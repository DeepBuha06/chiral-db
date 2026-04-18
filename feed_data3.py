# Copyright (c) 2026 Chiral Contributors
#
# This source code is licensed under the MIT license found in the
# LICENSE file in the root directory of this source tree.

"""Nested data feeder for two sessions (500 records each) to support multi-session demos."""

from __future__ import annotations

import asyncio
import json
import logging
import random
import time
from datetime import UTC, datetime

import httpx

CHIRAL_API_URL = "http://127.0.0.1:8000/ingest"
SESSION_IDS = ["session_demo_alpha", "session_demo_beta"]
RECORDS_PER_SESSION = 500
LOG_INTERVAL = 100
SUCCESS_STATUS = 200

logging.basicConfig(level=logging.INFO, format="%(message)s")
logging.getLogger("httpx").setLevel(logging.WARNING)
logger = logging.getLogger(__name__)


def _build_comment(comment_id: int) -> dict[str, object]:
    return {
        "comment_id": comment_id,
        "text": f"comment-{comment_id}",
        "score": round(random.uniform(0.0, 1.0), 3),
        "is_flagged": random.choice([True, False]),
        "meta": {
            "lang": random.choice(["en", "fr", "de"]),
            "sentiment": random.choice(["positive", "neutral", "negative"]),
        },
    }


def _build_event(event_id: int) -> dict[str, object]:
    return {
        "event_id": event_id,
        "event_type": random.choice(["view", "click", "purchase"]),
        "amount": round(random.uniform(5, 500), 2),
        "is_conversion": random.choice([True, False]),
        "extra": {
            "campaign": random.choice(["summer", "winter", "flash"]),
            "region": random.choice(["us", "eu", "apac"]),
        },
    }


def _generate_record(session_id: str, index: int) -> dict[str, object]:
    if session_id == "session_demo_alpha":
        return _generate_alpha_record(session_id, index)
    return _generate_beta_record(session_id, index)


def _generate_alpha_record(session_id: str, index: int) -> dict[str, object]:
    now = time.time()
    comment_count = random.randint(1, 4)
    event_count = random.randint(1, 3)

    return {
        "session_id": session_id,
        "username": f"{session_id}_user_{index % 50}",
        "sys_ingested_at": now,
        "t_stamp": now,
        "city": random.choice(["Paris", "Berlin", "Tokyo", "Delhi"]),
        "temperature": random.randint(15, 40),
        "device": random.choice(["android", "ios", "web"]),
        "metadata": {
            "source": "feed_data3_alpha",
            "generated_at": datetime.now(tz=UTC).isoformat(),
            "session_label": session_id,
            "variant": "alpha",
            "version": "3.1",
        },
        "comments": [_build_comment(index * 10 + offset) for offset in range(comment_count)],
        "events": [_build_event(index * 10 + offset) for offset in range(event_count)],
    }


def _generate_beta_record(session_id: str, index: int) -> dict[str, object]:
    now = time.time()
    action_count = random.randint(1, 5)
    item_count = random.randint(1, 4)

    return {
        "session_id": session_id,
        "user_handle": f"beta_{index % 80}",
        "sys_ingested_at": now,
        "t_stamp": now,
        "region": random.choice(["north", "south", "east", "west"]),
        "device_profile": {
            "family": random.choice(["mobile", "desktop", "tablet"]),
            "os_name": random.choice(["android", "ios", "linux", "windows"]),
            "app_version": random.choice(["1.4.0", "1.5.1", "1.6.0"]),
        },
        "metrics": {
            "score": round(random.uniform(10, 95), 2),
            "risk_tier": random.choice(["low", "medium", "high"]),
            "active_minutes": random.randint(3, 240),
        },
        "cart_items": [
            {
                "sku": f"SKU-{index % 30}-{offset}",
                "qty": random.randint(1, 5),
                "unit_price": round(random.uniform(8, 120), 2),
                "tags": random.sample(["promo", "fragile", "new", "bulk"], k=random.randint(1, 3)),
            }
            for offset in range(item_count)
        ],
        "actions": [
            {
                "action_name": random.choice(["search", "add_to_cart", "checkout", "refund"]),
                "latency_ms": random.randint(20, 900),
                "ok": random.choice([True, False]),
            }
            for _ in range(action_count)
        ],
        "context": {
            "source": "feed_data3_beta",
            "generated_at": datetime.now(tz=UTC).isoformat(),
            "session_label": session_id,
            "variant": "beta",
        },
    }


async def _flush_session(client: httpx.AsyncClient, session_id: str) -> None:
    flush_url = f"http://127.0.0.1:8000/flush/{session_id}"
    response = await client.post(flush_url)
    if response.status_code == SUCCESS_STATUS:
        logger.info("[Feeder3] Flush successful for %s: %s", session_id, json.dumps(response.json()))
    else:
        logger.error("[Feeder3] Flush failed for %s: %s", session_id, response.text)


async def feed() -> None:
    timeout = httpx.Timeout(30.0, read=None)
    async with httpx.AsyncClient(timeout=timeout) as client:
        total_target = len(SESSION_IDS) * RECORDS_PER_SESSION
        logger.info("[Feeder3] Sending %d total nested records to %s", total_target, CHIRAL_API_URL)

        for session_id in SESSION_IDS:
            logger.info("[Feeder3] Ingesting %d records for session: %s", RECORDS_PER_SESSION, session_id)
            sent = 0
            for index in range(RECORDS_PER_SESSION):
                payload = {"data": _generate_record(session_id, index)}
                response = await client.post(CHIRAL_API_URL, json=payload)
                if response.status_code == SUCCESS_STATUS:
                    sent += 1
                    if sent % LOG_INTERVAL == 0:
                        logger.info("[Feeder3] %s -> Ingested %d records...", session_id, sent)
                else:
                    logger.error("[Feeder3] %s -> Error %d: %s", session_id, response.status_code, response.text)

            logger.info("[Feeder3] Finished session %s. Total records sent: %d", session_id, sent)
            await _flush_session(client, session_id)

        logger.info("[Feeder3] All session ingestion complete.")


if __name__ == "__main__":
    asyncio.run(feed())
