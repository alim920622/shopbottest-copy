from __future__ import annotations

from app.db.database import Database

# Закрытые статусы, при которых чат без сообщений недоступен.
CLOSED_STATUSES: set[str] = {"finished", "canceled", "delivered"}


async def has_chat_messages(db: Database, order_id: int) -> bool:
    """Проверяет, есть ли хотя бы одно сообщение в чате заказа."""
    async with db.conn() as conn:
        cur = await conn.execute(
            "SELECT 1 FROM order_chat_messages WHERE order_id=? LIMIT 1",
            (order_id,),
        )
        return await cur.fetchone() is not None


async def can_access_order_chat(db: Database, order: dict) -> bool:
    """Определяет доступ к чату по единому правилу статуса и наличия переписки."""
    order_id = int(order.get("id") or 0)
    if order_id and await has_chat_messages(db, order_id):
        return True

    status = str(order.get("status") or "").strip().lower()
    if status in CLOSED_STATUSES:
        return False
    return True
