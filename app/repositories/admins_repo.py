from __future__ import annotations
from app.db.database import Database


class AdminsRepo:
    def __init__(self, db: Database):
        self.db = db

    async def list_admin_user_ids(self, shop_id: int) -> list[int]:
        async with self.db.conn() as conn:
            cur = await conn.execute(
                "SELECT user_id FROM shop_admins WHERE shop_id=?",
                (shop_id,),
            )
            rows = await cur.fetchall()
            return [int(r["user_id"]) for r in rows]
