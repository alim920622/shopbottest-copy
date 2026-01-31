from __future__ import annotations

from typing import Sequence, Optional

from app.db.database import Database


class PromotionsRepo:
    def __init__(self, db: Database):
        self.db = db

    async def create(self, shop_id: int, title: str, description: str = "") -> int:
        async with self.db.conn() as conn:
            cur = await conn.execute(
                """
                INSERT INTO promotions(shop_id, title, description)
                VALUES (?, ?, ?)
                """,
                (shop_id, title, description),
            )
            await conn.commit()
            return int(cur.lastrowid)

    async def list_for_shop(self, shop_id: int) -> Sequence[dict]:
        async with self.db.conn() as conn:
            cur = await conn.execute(
                """
                SELECT id, title, description, is_active, created_at
                FROM promotions
                WHERE shop_id=?
                ORDER BY created_at DESC
                """,
                (shop_id,),
            )
            rows = await cur.fetchall()
            return [dict(r) for r in rows]

    async def get(self, promo_id: int) -> Optional[dict]:
        async with self.db.conn() as conn:
            cur = await conn.execute(
                """
                SELECT id, shop_id, title, description, is_active, created_at
                FROM promotions
                WHERE id=?
                """,
                (promo_id,),
            )
            row = await cur.fetchone()
            return dict(row) if row else None

    async def attach_product(self, promo_id: int, product_id: int) -> None:
        async with self.db.conn() as conn:
            await conn.execute(
                """
                INSERT OR IGNORE INTO promotion_items(promo_id, product_id)
                VALUES (?, ?)
                """,
                (promo_id, product_id),
            )
            await conn.commit()

    async def list_items(self, promo_id: int) -> Sequence[dict]:
        async with self.db.conn() as conn:
            cur = await conn.execute(
                """
                SELECT p.id, p.name, p.price
                FROM promotion_items pi
                JOIN products p ON p.id = pi.product_id
                WHERE pi.promo_id=?
                ORDER BY p.name
                """,
                (promo_id,),
            )
            rows = await cur.fetchall()
            return [dict(r) for r in rows]
