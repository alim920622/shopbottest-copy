from __future__ import annotations

from aiogram import Router
from aiogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    InlineQuery,
    InlineQueryResultArticle,
    InputTextMessageContent,
)

from app.db.database import Database
from app.services.inline_search_service import InlineSearchService

router = Router()


def _clamp_text(value: str, limit: int) -> str:
    # Ограничиваем длину строк под лимиты Telegram.
    if len(value) <= limit:
        return value
    return value[:limit].rstrip() + "…"


def _format_price(value: object) -> str:
    # Форматируем цену единообразно без лишних нулей.
    if value is None:
        return ""
    try:
        number = float(value)
    except (TypeError, ValueError):
        return str(value)
    if number.is_integer():
        return str(int(number))
    return f"{number:.2f}"


def _inline_actions_markup(product_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="➕ В корзину", callback_data=f"c:add:{product_id}"),
            InlineKeyboardButton(text="📦 Открыть товар", callback_data=f"c:prod:{product_id}"),
        ]
    ])


@router.inline_query()
async def inline_search(inline_query: InlineQuery, db: Database):
    query = (inline_query.query or "").strip()
    if not query:
        await inline_query.answer([], cache_time=1, is_personal=True)
        return

    service = InlineSearchService(db)
    results = await service.search_products(query=query, limit=20)
    items: list[InlineQueryResultArticle] = []

    for item in results:
        product = item.product
        shop = item.shop
        price = product.get("price")
        price_text = _format_price(price) if price is not None else ""

        description_parts = []
        if price_text:
            description_parts.append(f"Цена: {price_text}")
        if shop.get("name"):
            description_parts.append(shop["name"])

        message_lines = [f"🛒 {product.get('name', '')}".strip()]
        if price_text:
            message_lines.append(f"💰 {price_text}")
        if product.get("description"):
            message_lines.append(f"\n{product['description']}")
        if shop.get("name"):
            message_lines.append(f"\n🏪 {shop['name']}")

        product_id = int(product.get("id"))
        shop_id = int(shop.get("id"))
        result_id = f"p:{product_id}:s:{shop_id}"
        message_text = _clamp_text("\n".join(message_lines).strip(), 4000)
        title = _clamp_text(product.get("name", "Товар"), 80)
        description = " • ".join(description_parts) if description_parts else ""
        description = _clamp_text(description, 240) if description else None
        items.append(
            InlineQueryResultArticle(
                id=result_id,
                title=title,
                description=description,
                input_message_content=InputTextMessageContent(message_text=message_text),
                reply_markup=_inline_actions_markup(product_id),
                thumb_url=product.get("photo_url") or None,
            )
        )

    await inline_query.answer(items, cache_time=5, is_personal=True)
