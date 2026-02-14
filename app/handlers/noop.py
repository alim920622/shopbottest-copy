from aiogram import Router, F
from aiogram.types import CallbackQuery

router = Router()

@router.callback_query(F.data == "noop")
async def noop(cq: CallbackQuery):
    await cq.answer()
