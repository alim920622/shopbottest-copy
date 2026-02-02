from aiogram import Router, F
from aiogram.filters import CommandStart
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext

from app.db.database import Database
from app.handlers_admin_restaurant.utils import is_restaurant_admin
from app.services.screen import clear_state_keep_screen, show_main_menu

router = Router()


def kb_admin_main() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🍽 Заказы", callback_data="r:orders")],
        [InlineKeyboardButton(text="🧾 Меню", callback_data="r:cats")],
        [InlineKeyboardButton(text="🕓 История", callback_data="r:history")],
        [InlineKeyboardButton(text="🎁 Акции", callback_data="r:promos")],
        [InlineKeyboardButton(text="👤 Кабинет", callback_data="r:cabinet")],
        [InlineKeyboardButton(text="💬 Чат", callback_data="r:chat")],
    ])


@router.message(CommandStart())
async def start_cmd(message: Message, db: Database, state: FSMContext):
    if not await is_restaurant_admin(db, message.from_user.id):
        await message.answer("Нет доступа. Ваш user_id не назначен админом ресторана.")
        return
    await clear_state_keep_screen(state)
    await show_main_menu(
        message.bot,
        message.chat.id,
        state,
        "Админ-меню ресторана:",
        kb_admin_main(),
    )


@router.callback_query(F.data == "r:home")
async def home(cq: CallbackQuery, db: Database, state: FSMContext):
    await clear_state_keep_screen(state)
    await cq.message.edit_text("Админ-меню ресторана:", reply_markup=kb_admin_main())
    await cq.answer()
