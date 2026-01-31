from __future__ import annotations

from typing import Optional

from app.db.database import Database


class ClientProfilesRepo:
    def __init__(self, db: Database):
        self.db = db

    async def get(self, user_id: int) -> Optional[dict]:
        async with self.db.conn() as conn:
            cur = await conn.execute(
                "SELECT user_id, full_name, phone, address FROM client_profiles WHERE user_id=?",
                (user_id,),
            )
            row = await cur.fetchone()
            return dict(row) if row else None

    async def upsert(self, user_id: int, full_name: str | None = None, phone: str | None = None,
                     address: str | None = None) -> None:
        async with self.db.conn() as conn:
            cur = await conn.execute(
                "SELECT user_id, full_name, phone, address FROM client_profiles WHERE user_id=?",
                (user_id,),
            )
            row = await cur.fetchone()
            if row:
                new_full_name = full_name if full_name is not None else row["full_name"]
                new_phone = phone if phone is not None else row["phone"]
                new_address = address if address is not None else row["address"]
                await conn.execute(
                    """
                    UPDATE client_profiles
                    SET full_name=?, phone=?, address=?
                    WHERE user_id=?
                    """,
                    (new_full_name, new_phone, new_address, user_id),
                )
            else:
                await conn.execute(
                    """
                    INSERT INTO client_profiles(user_id, full_name, phone, address)
                    VALUES (?, ?, ?, ?)
                    """,
                    (user_id, full_name or "", phone or "", address or ""),
                )
            await conn.commit()
