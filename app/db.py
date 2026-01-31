import aiosqlite
from dataclasses import dataclass
from typing import Optional

@dataclass
class User:
    user_id: int
    role: str  # "superadmin" | "admin" | "none"

class Database:
    def __init__(self, path: str):
        self.path = path

    async def init(self) -> None:
        async with aiosqlite.connect(self.path) as db:
            await db.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    user_id INTEGER PRIMARY KEY,
                    role TEXT NOT NULL
                )
            """)
            await db.commit()

    async def upsert_user(self, user_id: int, role: str) -> None:
        async with aiosqlite.connect(self.path) as db:
            await db.execute("""
                INSERT INTO users (user_id, role) VALUES (?, ?)
                ON CONFLICT(user_id) DO UPDATE SET role=excluded.role
            """, (user_id, role))
            await db.commit()

    async def get_user(self, user_id: int) -> Optional[User]:
        async with aiosqlite.connect(self.path) as db:
            cur = await db.execute("SELECT user_id, role FROM users WHERE user_id=?", (user_id,))
            row = await cur.fetchone()
            if not row:
                return None
            return User(user_id=row[0], role=row[1])
