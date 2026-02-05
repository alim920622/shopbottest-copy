from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

from app.db.database import Database
from app.repositories.shops_repo import ShopsRepo
from app.services.search_service import SearchService, SearchResult


@dataclass(frozen=True)
class InlineSearchItem:
    product: dict
    score: float
    shop: dict


class InlineSearchService:
    def __init__(self, db: Database):
        self.db = db

    async def search_products(self, query: str, limit: int = 20) -> Sequence[InlineSearchItem]:
        shops_repo = ShopsRepo(self.db)
        # Inline-поиск доступен только по магазинам.
        shops = await shops_repo.list_active(business_type="shop")
        if not shops:
            return []

        service = SearchService(self.db)
        combined: list[InlineSearchItem] = []
        per_shop_limit = max(5, limit)
        for shop in shops:
            results = await service.search_products(
                shop_id=int(shop["id"]),
                query=query,
                limit=per_shop_limit,
                active_only=True,
            )
            combined.extend(self._wrap_results(results, shop))

        combined.sort(key=lambda item: item.score, reverse=True)
        return combined[:limit]

    @staticmethod
    def _wrap_results(results: Sequence[SearchResult], shop: dict) -> list[InlineSearchItem]:
        items: list[InlineSearchItem] = []
        for res in results:
            items.append(InlineSearchItem(product=res.product, score=res.score, shop=shop))
        return items
