from __future__ import annotations

from aiogram import Router
from aiogram.types import InlineQuery, InlineQueryResultArticle, InputTextMessageContent

from app.db.database import Database
from app.services.inline_search_service import InlineSearchService

router = Router()


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
        price_text = f"{price}" if price is not None else ""

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

        result_id = f"product_{product.get('id')}_{shop.get('id')}"
        items.append(
            InlineQueryResultArticle(
                id=result_id,
                title=product.get("name", "Товар"),
                description=" • ".join(description_parts) if description_parts else None,
                input_message_content=InputTextMessageContent("\n".join(message_lines).strip()),
                thumb_url=product.get("photo_url") or None,
            )
        )

    await inline_query.answer(items, cache_time=5, is_personal=True)
