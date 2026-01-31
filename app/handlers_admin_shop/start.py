from aiogram import Router, F
from aiogram.filters import CommandStart
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext

from app.db.database import Database
from app.handlers_admin_shop.utils import is_shop_admin

router = Router()


def kb_admin_main():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📦 Заказы", callback_data="a:orders")],
        [InlineKeyboardButton(text="🧺 Продукты", callback_data="a:products")],
        [InlineKeyboardButton(text="🕓 История",  callback_data="a:history")],
        [InlineKeyboardButton(text="🎁 Акции",    callback_data="a:promos")],
        [InlineKeyboardButton(text="💬 Чат",    callback_data="a:chat")],
        [InlineKeyboardButton(text="👤 Кабинет",  callback_data="a:cabinet")],
    ])


@router.message(CommandStart())
async def start_cmd(message: Message, db: Database):
    if not await is_shop_admin(db, message.from_user.id):
        await message.answer("Нет доступа. Ваш user_id не назначен админом магазина.")
        return

    await message.answer("Админ-меню магазина:", reply_markup=kb_admin_main())


@router.callback_query(F.data == "a:home")
async def home(cq, db: Database, state: FSMContext):
    # Быстрый возврат в главное меню
    await state.clear()
    await cq.message.edit_text("Админ-меню магазина:", reply_markup=kb_admin_main())
    await cq.answer()
