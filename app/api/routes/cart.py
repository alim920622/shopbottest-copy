from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from typing import List

from app.api.deps import get_current_user, get_db, CurrentUser
from app.db.database import Database
from app.repositories.cart_repo import CartRepo

router = APIRouter(prefix="/cart", tags=["cart"])


class CartItemIn(BaseModel):
    product_id: int = Field(gt=0)
    quantity: int = Field(ge=0)


class CartSyncRequest(BaseModel):
    items: List[CartItemIn]


@router.get("")
async def get_cart(
    user: CurrentUser = Depends(get_current_user),
    db: Database = Depends(get_db),
) -> dict:
    repo = CartRepo(db)
    items = await repo.list_items(user.user_id)
    return {"items": [dict(i) for i in items]}


@router.post("/item")
async def upsert_item(
    payload: CartItemIn,
    user: CurrentUser = Depends(get_current_user),
    db: Database = Depends(get_db),
) -> dict:
    repo = CartRepo(db)
    await repo.set_qty(user.user_id, payload.product_id, payload.quantity)
    items = await repo.list_items(user.user_id)
    return {"items": [dict(i) for i in items]}


@router.delete("")
async def clear_cart(
    user: CurrentUser = Depends(get_current_user),
    db: Database = Depends(get_db),
) -> dict:
    repo = CartRepo(db)
    await repo.clear(user.user_id)
    return {"ok": True}


@router.post("/sync")
async def sync_cart(
    payload: CartSyncRequest,
    user: CurrentUser = Depends(get_current_user),
    db: Database = Depends(get_db),
) -> dict:
    repo = CartRepo(db)
    server_items = await repo.list_items(user.user_id)
    if server_items:
        return {"items": [dict(i) for i in server_items], "source": "server"}
    async with db.conn() as conn:
        for item in payload.items:
            if item.quantity > 0:
                await conn.execute(
                    "INSERT INTO cart (user_id, product_id, quantity) VALUES (?, ?, ?) ON CONFLICT(user_id, product_id) DO UPDATE SET quantity=excluded.quantity",
                    (user.user_id, item.product_id, item.quantity),
                )
        await conn.commit()
    items = await repo.list_items(user.user_id)
    return {"items": [dict(i) for i in items], "source": "local"}
