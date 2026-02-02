from aiogram import Router
from aiogram.types import Message
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext

from app.handlers_client.kb import kb_client_main
from app.services.screen import clear_state_keep_screen, show_main_menu

router = Router()


@router.message(CommandStart())
async def start_cmd(message: Message, state: FSMContext):
    await clear_state_keep_screen(state)
    await show_main_menu(
        message.bot,
        message.chat.id,
        state,
        "Добро пожаловать! Выберите раздел:",
        kb_client_main(),
    )
