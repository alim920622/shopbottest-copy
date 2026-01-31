import asyncio
from pathlib import Path
import tempfile

from app.db.database import Database, DBConfig
from app.repositories.shops_repo import ShopsRepo
from app.repositories.categories_repo import CategoriesRepo
from app.repositories.products_repo import ProductsRepo
from app.services.search_service import SearchService


def test_search_service_fuzzy_and_synonyms():
    async def _run():
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test.db"
            db = Database(DBConfig(path=str(db_path)))
            await db.init_schema()

            shops = ShopsRepo(db)
            shop_id = await shops.create_shop("Магазин 1", "shop")
            cats = CategoriesRepo(db)
            cat_id = await cats.create(shop_id, "Молочка")

            products = ProductsRepo(db)
            await products.create(shop_id, cat_id, "Молоко", 50.0, "Свежее молоко")
            await products.create(shop_id, cat_id, "Картофель", 30.0, "Фермерский")

            async with db.conn() as conn:
                await conn.execute(
                    "INSERT INTO search_synonyms(shop_id, term, synonym) VALUES (?, ?, ?)",
                    (shop_id, "картофель", "картошка"),
                )
                await conn.commit()

            service = SearchService(db)

            results_partial = await service.search_products(shop_id, "мол")
            assert any(r.product["name"] == "Молоко" for r in results_partial)

            results_fuzzy = await service.search_products(shop_id, "малако")
            assert any(r.product["name"] == "Молоко" for r in results_fuzzy)

            results_syn = await service.search_products(shop_id, "картошка")
            assert any(r.product["name"] == "Картофель" for r in results_syn)

            results_empty = await service.search_products(shop_id, "несуществующий")
            assert results_empty == []

    asyncio.run(_run())
