from __future__ import annotations

from aiogram import Bot
from aiogram.fsm.context import FSMContext
from aiogram.types import InlineKeyboardMarkup
from aiogram.exceptions import TelegramBadRequest

SCREEN_MESSAGE_ID_KEY = "screen_message_id"


async def get_screen_message_id(state: FSMContext) -> int | None:
    data = await state.get_data()
    return data.get(SCREEN_MESSAGE_ID_KEY)


async def set_screen_message_id(state: FSMContext, message_id: int) -> None:
    await state.update_data({SCREEN_MESSAGE_ID_KEY: message_id})


async def clear_screen_message_id(state: FSMContext) -> None:
    await state.update_data({SCREEN_MESSAGE_ID_KEY: None})


async def clear_state_keep_screen(state: FSMContext) -> None:
    screen_message_id = await get_screen_message_id(state)
    await state.clear()
    if screen_message_id:
        await set_screen_message_id(state, screen_message_id)


async def delete_screen(bot: Bot, chat_id: int, state: FSMContext) -> None:
    screen_message_id = await get_screen_message_id(state)
    if not screen_message_id:
        return
    try:
        await bot.delete_message(chat_id=chat_id, message_id=screen_message_id)
    except Exception:
        # Безопасно игнорируем, чтобы не зациклиться на недоступном сообщении.
        pass
    await clear_screen_message_id(state)


async def show_screen(
    bot: Bot,
    chat_id: int,
    state: FSMContext,
    text: str,
    reply_markup: InlineKeyboardMarkup | None,
) -> int:
    screen_message_id = await get_screen_message_id(state)
    if screen_message_id:
        try:
            await bot.edit_message_text(
                text=text,
                chat_id=chat_id,
                message_id=screen_message_id,
                reply_markup=reply_markup,
            )
            return screen_message_id
        except TelegramBadRequest as exc:
            if "message is not modified" in str(exc):
                return screen_message_id
        except Exception:
            pass

    message = await bot.send_message(chat_id=chat_id, text=text, reply_markup=reply_markup)
    await set_screen_message_id(state, message.message_id)
    return message.message_id


async def show_main_menu(
    bot: Bot,
    chat_id: int,
    state: FSMContext,
    text: str,
    reply_markup: InlineKeyboardMarkup,
) -> int:
    return await show_screen(
        bot=bot,
        chat_id=chat_id,
        state=state,
        text=text,
        reply_markup=reply_markup,
    )
