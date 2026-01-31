from __future__ import annotations
from typing import Optional, Sequence
from app.db.database import Database
from app.services.search_utils import normalize_text


class CategoriesRepo:
    def __init__(self, db: Database):
        self.db = db

    async def create(self, shop_id: int, name: str, sort: int = 0) -> int:
        name_norm = normalize_text(name)
        async with self.db.conn() as conn:
            cur = await conn.execute(
                "INSERT INTO categories (shop_id, name, name_norm, sort) VALUES (?, ?, ?, ?)",
                (shop_id, name, name_norm, sort),
            )
            await conn.commit()
            return int(cur.lastrowid)

    async def rename(self, category_id: int, new_name: str) -> None:
        async with self.db.conn() as conn:
            await conn.execute(
                "UPDATE categories SET name=?, name_norm=? WHERE id=?",
                (new_name, normalize_text(new_name), category_id),
            )
            await conn.commit()

    async def set_active(self, category_id: int, is_active: bool) -> None:
        async with self.db.conn() as conn:
            await conn.execute(
                "UPDATE categories SET is_active=? WHERE id=?",
                (1 if is_active else 0, category_id),
            )
            await conn.commit()

    async def list_for_shop(self, shop_id: int, active_only: bool = True) -> Sequence[dict]:
        q = "SELECT * FROM categories WHERE shop_id=?"
        params = [shop_id]
        if active_only:
            q += " AND is_active=1"
        q += " ORDER BY sort ASC, id ASC"
        async with self.db.conn() as conn:
            cur = await conn.execute(q, params)
            rows = await cur.fetchall()
            return [dict(r) for r in rows]

    async def get(self, category_id: int) -> Optional[dict]:
        async with self.db.conn() as conn:
            cur = await conn.execute("SELECT * FROM categories WHERE id=?", (category_id,))
            row = await cur.fetchone()
            return dict(row) if row else None
