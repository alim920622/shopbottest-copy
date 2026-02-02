from aiogram import Router, F
from aiogram.types import Message
from aiogram.fsm.context import FSMContext

from app.db.database import Database
from app.handlers_admin_restaurant.start import kb_admin_main
from app.handlers_admin_restaurant.utils import is_restaurant_admin
from app.services.screen import delete_screen, show_main_menu

router = Router()


@router.message(F.text)
async def fallback_handler(message: Message, state: FSMContext, db: Database):
    if await state.get_state() is not None:
        return
    if message.text and message.text.startswith("/"):
        return
    if not await is_restaurant_admin(db, message.from_user.id):
        await message.answer("Нет доступа. Ваш user_id не назначен админом ресторана.")
        return
    await delete_screen(message.bot, message.chat.id, state)
    await message.answer("Я не понял команду. Используйте меню ниже.")
    await show_main_menu(
        message.bot,
        message.chat.id,
        state,
        "Админ-меню ресторана:",
        kb_admin_main(),
    )
