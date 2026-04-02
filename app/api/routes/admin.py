from __future__ import annotations
import os
from fastapi import APIRouter, HTTPException, Query
from app.api.deps import get_db
from app.db.database import Database
from fastapi import Depends

router = APIRouter(prefix="/admin", tags=["admin"])
ADMIN_SECRET = os.getenv("ADMIN_SECRET", "sabad_admin_secret_2024")

def check_secret(secret: str = Query(...)):
    if secret != ADMIN_SECRET:
        raise HTTPException(status_code=403, detail="Forbidden")

@router.get("/shops")
async def get_shops(secret: str = Query(...), db: Database = Depends(get_db)):
    check_secret(secret)
    async with db.conn() as conn:
        cur = await conn.execute("SELECT id, name, business_type, address, phone, is_active FROM shops ORDER BY id")
        rows = await cur.fetchall()
        return {"items": [dict(r) for r in rows]}

@router.get("/products")
async def get_products(secret: str = Query(...), limit: int = 100, offset: int = 0, db: Database = Depends(get_db)):
    check_secret(secret)
    async with db.conn() as conn:
        cur = await conn.execute(
            "SELECT p.id, p.name, p.price, p.is_active, p.category_id, p.shop_id, s.name as shop_name FROM products p JOIN shops s ON s.id=p.shop_id ORDER BY p.id DESC LIMIT $1 OFFSET $2",
            (limit, offset)
        )
        rows = await cur.fetchall()
        cur2 = await conn.execute("SELECT COUNT(*) as cnt FROM products")
        total = (await cur2.fetchone())["cnt"]
        return {"items": [dict(r) for r in rows], "total": total}

@router.get("/orders")
async def get_orders(secret: str = Query(...), limit: int = 50, offset: int = 0, db: Database = Depends(get_db)):
    check_secret(secret)
    async with db.conn() as conn:
        cur = await conn.execute(
            "SELECT o.*, s.name as shop_name FROM orders o JOIN shops s ON s.id=o.shop_id ORDER BY o.id DESC LIMIT $1 OFFSET $2",
            (limit, offset)
        )
        rows = await cur.fetchall()
        cur2 = await conn.execute("SELECT COUNT(*) as cnt FROM orders")
        total = (await cur2.fetchone())["cnt"]
        return {"items": [dict(r) for r in rows], "total": total}

@router.get("/users")
async def get_users(secret: str = Query(...), limit: int = 50, offset: int = 0, db: Database = Depends(get_db)):
    check_secret(secret)
    async with db.conn() as conn:
        cur = await conn.execute(
            "SELECT u.user_id, u.role, u.created_at, cp.full_name, cp.phone FROM users u LEFT JOIN client_profiles cp ON cp.user_id=u.user_id ORDER BY u.user_id DESC LIMIT $1 OFFSET $2",
            (limit, offset)
        )
        rows = await cur.fetchall()
        cur2 = await conn.execute("SELECT COUNT(*) as cnt FROM users")
        total = (await cur2.fetchone())["cnt"]
        return {"items": [dict(r) for r in rows], "total": total}

@router.get("/cart")
async def get_cart(secret: str = Query(...), db: Database = Depends(get_db)):
    check_secret(secret)
    async with db.conn() as conn:
        cur = await conn.execute(
            "SELECT c.user_id, c.quantity, p.name, p.price, s.name as shop_name FROM cart c JOIN products p ON p.id=c.product_id JOIN shops s ON s.id=p.shop_id ORDER BY c.user_id"
        )
        rows = await cur.fetchall()
        return {"items": [dict(r) for r in rows]}

@router.get("/categories")
async def get_categories(secret: str = Query(...), db: Database = Depends(get_db)):
    check_secret(secret)
    async with db.conn() as conn:
        cur = await conn.execute(
            "SELECT c.id, c.name, c.is_active, s.name as shop_name FROM categories c JOIN shops s ON s.id=c.shop_id ORDER BY c.shop_id, c.id"
        )
        rows = await cur.fetchall()
        return {"items": [dict(r) for r in rows]}

@router.get("/stats")
async def get_stats(secret: str = Query(...), db: Database = Depends(get_db)):
    check_secret(secret)
    async with db.conn() as conn:
        stats = {}
        for table in ["shops","products","orders","users","cart","categories"]:
            cur = await conn.execute(f"SELECT COUNT(*) as cnt FROM {table}")
            row = await cur.fetchone()
            stats[table] = row["cnt"]
        cur = await conn.execute("SELECT COUNT(*) as cnt FROM orders WHERE status='new'")
        stats["orders_new"] = (await cur.fetchone())["cnt"]
        cur = await conn.execute("SELECT COUNT(*) as cnt FROM products WHERE is_active=1")
        stats["products_active"] = (await cur.fetchone())["cnt"]
        return stats

from pydantic import BaseModel
from typing import Optional

class ShopCreate(BaseModel):
    name: str
    business_type: str  # "restaurant" или "shop"
    address: str
    phone: str
    description: Optional[str] = None
    is_active: bool = True

@router.post("/shops")
async def create_shop(payload: ShopCreate, secret: str = Query(...), db: Database = Depends(get_db)):
    check_secret(secret)
    if payload.business_type not in ("restaurant", "shop"):
        raise HTTPException(status_code=400, detail="business_type must be 'restaurant' or 'shop'")
    async with db.conn() as conn:
        cur = await conn.execute(
            "INSERT INTO shops (name, business_type, address, phone, is_active) VALUES ($1, $2, $3, $4, $5) RETURNING id",
            (payload.name, payload.business_type, payload.address, payload.phone, payload.is_active)
        )
        row = await cur.fetchone()
        return {"id": row["id"], "name": payload.name, "business_type": payload.business_type}
