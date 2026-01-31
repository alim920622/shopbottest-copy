from aiogram import Router
from aiogram.types import Message
from aiogram.filters import CommandStart

from app.handlers_client.kb import kb_client_main

router = Router()


@router.message(CommandStart())
async def start_cmd(message: Message):
    await message.answer("Добро пожаловать! Выберите раздел:", reply_markup=kb_client_main())
