import asyncio
from app.db.database import Database, DBConfig

async def main():
    db = Database(DBConfig(path="shop.db"))
    await db.init_schema()
    print("OK: schema initialized")

    async with db.conn() as conn:
        cur = await conn.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name;")
        rows = await cur.fetchall()
        print("Tables:", [r["name"] for r in rows])

if __name__ == "__main__":
    asyncio.run(main())
