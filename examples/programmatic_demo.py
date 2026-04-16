# Copyright (c) 2026 Chiral Contributors
#
# This source code is licensed under the MIT license found in the
# LICENSE file in the root directory of this source tree.

"""Advanced demonstration of ChiralDB's autonomous normalization engine."""

import asyncio
import json
from sqlalchemy import text
from chiral.client import ChiralClient
from chiral.config import get_settings

SESSION_ID = "advanced_demo_01"

def print_header(title: str) -> None:
    print(f"\n{'=' * 80}\n{title}\n{'=' * 80}")

async def main() -> None:
    settings = get_settings()
    
    async with ChiralClient(settings.database_url) as db:
        print_header("1. INGESTING NESTED DATA")
        print("Feeding deeply nested JSON arrays into ChiralDB...")
        
        # We ingest multiple records to trigger the array decomposition engine
        for i in range(5):
            record = {
                "username": f"user_{i}",
                "device": "macOS",
                "events": [
                    {"event_type": "click", "x": 100 * i, "y": 200 * i},
                    {"event_type": "scroll", "x": 0, "y": 500 * i}
                ]
            }
            await db.ingest(session_id=SESSION_ID, data=record)
            
        print("Flushing staging data to force Autonomous Evolve Phase...")
        await db.flush(SESSION_ID)

        print_header("2. UNDER THE HOOD: POSTGRESQL TABLES")
        print("Because the 'events' array was homogeneous, ChiralDB automatically split it into a child SQL table!")
        
        async with db.engine.connect() as conn:
            # Query PostgreSQL's internal schema to prove the table was created
            result = await conn.execute(text(
                "SELECT table_name FROM information_schema.tables WHERE table_schema = 'public'"
            ))
            tables = [row[0] for row in result.fetchall()]
            
            print(f"Current Physical Tables in PostgreSQL: {tables}")
            if "chiral_data_events" in tables:
                print("✅ SUCCESS: 'chiral_data_events' child table was autonomously generated!")

        print_header("3. QUERYING THE LOGICAL SCHEMA")
        print("Users don't need to know about the child tables. They just query logically:")
        
        query_request = {
            "operation": "read",
            "session_id": SESSION_ID,
            "select": ["username", "device", "events.event_type", "events.y"],
            "filters": [
                {"field": "events.y", "op": "gte", "value": 500}
            ]
        }
        
        print(f"\nExecuting Query: {json.dumps(query_request, indent=2)}")
        
        result = await db.query(query_request)
        print(f"\nSQL Executed under the hood:\n{result.get('sql')}")
        print(f"\nResults returned (Rows: {result.get('row_count')}):")
        print(json.dumps(result.get('rows'), indent=2))

if __name__ == "__main__":
    asyncio.run(main())
