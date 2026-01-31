from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton


def kb_nav(home_cb: str, back_cb: str, home_text: str = "🏠 Главная", back_text: str = "🔙 Назад") -> InlineKeyboardMarkup:
    """
    Универсальная навигация в 1 ряд:
    слева — Главная
    справа — Назад
    """
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text=home_text, callback_data=home_cb),
            InlineKeyboardButton(text=back_text, callback_data=back_cb),
        ]
    ])
