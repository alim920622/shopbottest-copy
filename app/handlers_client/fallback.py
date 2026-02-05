from aiogram import Router, F
from aiogram.types import Message
from aiogram.fsm.context import FSMContext

from app.handlers_client.kb import kb_client_main
from app.services.screen import delete_screen, show_main_menu

router = Router()


@router.message(F.text)
async def fallback_handler(message: Message, state: FSMContext):
    # ✅ Сообщения, отправленные "via bot" (inline-результаты @username),
    # не должны вызывать fallback, иначе бот спамит "Я не понял команду".
    if message.via_bot is not None:
        return

    if await state.get_state() is not None:
        return
    if message.text and message.text.startswith("/"):
        return

    await delete_screen(message.bot, message.chat.id, state)
    await message.answer("Я не понял команду. Используйте меню ниже.")
    await show_main_menu(
        message.bot,
        message.chat.id,
        state,
        "Выберите раздел:",
        kb_client_main(),
    )
