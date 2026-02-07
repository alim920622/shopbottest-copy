from aiogram import Router, F
from aiogram.types import Message
from aiogram.fsm.context import FSMContext

from app.db.database import Database
from app.handlers_admin_shop.start import kb_admin_main
from app.handlers_admin_shop.utils import is_shop_admin
from app.services.screen import delete_screen, show_main_menu

router = Router()


@router.message(F.text)
async def fallback_handler(message: Message, state: FSMContext, db: Database):
    if message.via_bot is not None:
        return
    if await state.get_state() is not None:
        return
    if message.text and message.text.startswith("/"):
        return
    if not await is_shop_admin(db, message.from_user.id):
        await message.answer("Нет доступа. Ваш user_id не назначен админом магазина.")
        return
    await delete_screen(message.bot, message.chat.id, state, db, "admin_shop")
    await message.answer("Я не понял команду. Используйте меню ниже.")
    await show_main_menu(
        message.bot,
        message.chat.id,
        state,
        db,
        "admin_shop",
        "Админ-меню магазина:",
        kb_admin_main(),
    )
