from app.db.database import Database


async def get_admin_restaurant_ids(db: Database, user_id: int) -> list[int]:
    """
    Возвращает только те shop_id, которые являются restaurants.
    """
    async with db.conn() as conn:
        cur = await conn.execute(
            """
            SELECT sa.shop_id
            FROM shop_admins sa
            JOIN shops s ON s.id = sa.shop_id
            WHERE sa.user_id=? AND s.business_type='restaurant'
            """,
            (user_id,),
        )
        rows = await cur.fetchall()
        return [int(r["shop_id"]) for r in rows]


async def is_restaurant_admin(db: Database, user_id: int) -> bool:
    ids = await get_admin_restaurant_ids(db, user_id)
    return len(ids) > 0
