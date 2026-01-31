import asyncio
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage

from app.config import get_settings
from app.db import Database
from app.middlewares import AuthMiddleware

from app.handlers import start, menu

async def main():
    settings = get_settings()
    bot = Bot(token=settings.bot_token)
    dp = Dispatcher(storage=MemoryStorage())

    db = Database(settings.db_path)
    await db.init()

    dp.message.middleware(AuthMiddleware(settings, db))
    dp.callback_query.middleware(AuthMiddleware(settings, db))

    dp.include_router(start.router)
    dp.include_router(menu.router)

    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())

