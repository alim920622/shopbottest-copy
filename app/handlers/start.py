from aiogram import Router
from aiogram.types import Message
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from app.states import MenuStates
from app.keyboards import kb_main

router = Router()

@router.message(CommandStart())
async def start_cmd(message: Message, state: FSMContext, auth_role: str):
    if auth_role == "none":
        await message.answer("Доступ запрещён. Ваш user_id не добавлен в список администраторов.")
        return

    await state.set_state(MenuStates.main)
    await message.answer("Главное меню:", reply_markup=kb_main())
