from __future__ import annotations

import os

import uvicorn
from dotenv import load_dotenv
from fastapi import FastAPI

from app.api.routes.auth import router as auth_router
from app.api.routes.catalog import router as catalog_router
from app.api.routes.chats import router as chats_router
from app.api.routes.orders import router as orders_router
from app.db.database import DBConfig, Database


load_dotenv()


def create_app() -> FastAPI:
    app = FastAPI(title="ShopBot API", version="0.1.0")
    db_path = os.getenv("DB_PATH", "shop.db")
    app.state.db = Database(DBConfig(path=db_path))

    app.include_router(auth_router)
    app.include_router(catalog_router)
    app.include_router(orders_router)
    app.include_router(chats_router)

    @app.get("/health", tags=["system"])
    async def health() -> dict:
        return {"ok": True}

    return app


app = create_app()


if __name__ == "__main__":
    uvicorn.run("app.api.main:app", host="0.0.0.0", port=int(os.getenv("API_PORT", "8000")), reload=False)
