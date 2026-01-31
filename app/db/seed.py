import asyncio

from app.db.database import Database, DBConfig
from app.repositories.shops_repo import ShopsRepo
from app.repositories.categories_repo import CategoriesRepo
from app.repositories.products_repo import ProductsRepo


async def main():
    db = Database(DBConfig(path="shop.db"))
    await db.init_schema()

    shops = ShopsRepo(db)
    cats = CategoriesRepo(db)
    prod = ProductsRepo(db)

    # 1) Создаем 1 магазин и 1 ресторан
    shop_id = await shops.create_shop(name="Магазин №1", business_type="shop", phone="+992900000000", address="Адрес магазина 1")
    rest_id = await shops.create_shop(name="Ресторан №1", business_type="restaurant", phone="+992911111111", address="Адрес ресторана 1")

    # 2) Категории магазина
    veg_id = await cats.create(shop_id, "Овощи", sort=1)
    fruit_id = await cats.create(shop_id, "Фрукты", sort=2)

    # 3) Категории ресторана
    hot_id = await cats.create(rest_id, "Горячие", sort=1)
    drinks_id = await cats.create(rest_id, "Напитки", sort=2)

    # 4) Товары магазина
    await prod.create(shop_id, veg_id, "Картофель", 5.5, "1 кг")
    await prod.create(shop_id, veg_id, "Помидоры", 12.0, "1 кг")
    await prod.create(shop_id, fruit_id, "Яблоки", 10.0, "1 кг")

    # 5) Блюда ресторана
    await prod.create(rest_id, hot_id, "Бургер классический", 35.0, "Говядина, сыр, соус")
    await prod.create(rest_id, hot_id, "Шаверма", 30.0, "Курица, овощи, соус")
    await prod.create(rest_id, drinks_id, "Кола 0.5", 10.0, "0.5 л")

    print("OK: seeded demo data")
    print("Shop ID:", shop_id, "Restaurant ID:", rest_id)


if __name__ == "__main__":
    asyncio.run(main())
