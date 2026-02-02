from aiogram import Router, F
from aiogram.types import Message
from aiogram.fsm.context import FSMContext

from app.keyboards import kb_main
from app.services.screen import delete_screen, show_main_menu

router = Router()


@router.message(F.text)
async def fallback_handler(message: Message, state: FSMContext, auth_role: str):
    if await state.get_state() is not None:
        return
    if message.text and message.text.startswith("/"):
        return
    if auth_role == "none":
        await message.answer("Доступ запрещён. Ваш user_id не добавлен в список администраторов.")
        return
    await delete_screen(message.bot, message.chat.id, state)
    await message.answer("Я не понял команду. Используйте меню ниже.")
    await show_main_menu(message.bot, message.chat.id, state, "Главное меню:", kb_main())
