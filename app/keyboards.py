from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

def kb_main() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Заказы", callback_data="m:orders")],
        [InlineKeyboardButton(text="История", callback_data="m:history")],
        [InlineKeyboardButton(text="Акции", callback_data="m:promos")],
        [InlineKeyboardButton(text="Кабинет", callback_data="m:cabinet")],
        [InlineKeyboardButton(text="Продукты", callback_data="m:products")],
    ])

def kb_back(to: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Назад", callback_data=f"back:{to}")]
    ])
