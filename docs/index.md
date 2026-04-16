# ChiralDB

**ChiralDB** is an autonomous, session-scoped database framework that transparently bridges the gap between Relational (SQL) and Document (JSONB) paradigms over a single PostgreSQL instance.

Modern software systems increasingly operate on data whose structure is unknown at design time. ChiralDB abstracts database selection, schema handling, and transactional coordination completely away from the user.

---

## ⚡ The Magic of ChiralDB

With traditional databases, you have to choose: the strict safety of SQL, or the flexible chaos of NoSQL. **ChiralDB gives you both, automatically.**

You simply throw raw JSON at the ingestion engine. Behind the scenes, ChiralDB:

1. **Observes the data stream** using Shannon Entropy to infer types and stability.
2. **Dynamically creates PostgreSQL tables** for stable scalars and repeating arrays.
3. **Gracefully spills over** highly nested, sparse, or drifting data into `JSONB` columns.
4. **Reconstructs the data** on read, autonomously executing complex `LEFT JOIN`s and `jsonb_set` updates so you only ever have to think about logical JSON objects.

## 🛠️ Quick Glance

Using ChiralDB in your async Python application is incredibly simple. You don't write DDL. You don't write SQL. You just use data.

```python
import asyncio
from chiral.client import ChiralClient

async def main():
    async with ChiralClient("postgresql+asyncpg://user:pass@localhost:5432/db") as db:
        
        # 1. Ingest arbitrary, schema-less data
        await db.ingest(
            session_id="experiment_01", 
            data={
                "username": "devansh", 
                "sensors": [{"type": "temp", "val": 22}, {"type": "humid", "val": 40}]
            }
        )
        
        # 2. Query it logically. ChiralDB handles the SQL Joins and JSONB unpacking!
        result = await db.query({
            "operation": "read",
            "session_id": "experiment_01",
            "select": ["username", "sensors.val"],
            "filters": [{"field": "sensors.val", "op": "gt", "value": 20}]
        })
        
        print(result["rows"])

if __name__ == "__main__":
    asyncio.run(main())
```

---

## 🚀 Next Steps

Ready to get started? 

* Head over to [**Installation & Setup**](getting_started/installation.md) to install the package and spin up the built-in React Dashboard.
* Check out the [**Python Client API**](guide/client_api.md) to see how to integrate ChiralDB into your code.